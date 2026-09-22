"""Phase 0 audit of the raw yield dataset: leakage checks, data quality,
Maharashtra coverage for the 8 target crops. Writes reports/eda/eda_report.md
and plots, and saves the cleaned ALL-INDIA frame to
data/processed/yield_clean.parquet.
"""
from __future__ import annotations

import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from agriopt.config import (
    CROPS,
    CROP_NAME_MAP,
    DATA_PROCESSED,
    REPORTS_EDA,
    STATE,
    YIELD_CLEAN_PARQUET,
    YIELD_RAW_CSV,
)
from agriopt.data.yield_data import (
    clean_yield_data,
    correlation_fert_pesticide_area,
    find_duplicates,
    find_invalid_areas,
    find_outliers_iqr,
    leakage_yield_vs_production,
    load_raw_yield,
    maharashtra_target_counts,
)

WEAK_DATA_ROW_THRESHOLD = 10


def main() -> None:
    REPORTS_EDA.mkdir(parents=True, exist_ok=True)
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

    print(f"Loading raw yield data from {YIELD_RAW_CSV} ...")
    df = load_raw_yield()
    print(f"Loaded {len(df)} rows, {len(df.columns)} columns.")

    lines: list[str] = []
    lines.append("# Yield dataset audit\n")
    lines.append(f"Source: `{YIELD_RAW_CSV}`\n")

    # --- a) shape, dtypes, nulls, year range, #states, #crops --------------
    lines.append("## a) Overview\n")
    lines.append(f"- Shape: {df.shape[0]} rows x {df.shape[1]} columns\n")
    lines.append("- Dtypes:\n")
    for col, dt in df.dtypes.items():
        lines.append(f"  - `{col}`: {dt}\n")
    nulls = df.isna().sum()
    lines.append("- Null counts:\n")
    for col, n in nulls.items():
        lines.append(f"  - `{col}`: {n}\n")
    lines.append(f"- Year range: {df['Crop_Year'].min()}-{df['Crop_Year'].max()}\n")
    lines.append(f"- #States: {df['State'].nunique()}\n")
    lines.append(f"- #Crops: {df['Crop'].nunique()}\n")

    # --- b) Maharashtra rows per target crop per season ---------------------
    lines.append(f"\n## b) {STATE} rows per target crop per season\n")
    mh_counts = maharashtra_target_counts(df, state=STATE)
    lines.append("\n| crop | season | n_rows |\n|---|---|---|\n")
    for _, row in mh_counts.iterrows():
        lines.append(f"| {row['crop']} | {row['season']} | {row['n_rows']} |\n")

    weak_crops = sorted(
        mh_counts.groupby("crop")["n_rows"].sum()[
            lambda s: s < WEAK_DATA_ROW_THRESHOLD
        ].index.tolist()
    )
    lines.append(
        f"\n**Weak-data crops** (total {STATE} rows < {WEAK_DATA_ROW_THRESHOLD}): "
        f"{weak_crops if weak_crops else 'none'}\n"
    )
    if weak_crops:
        print(f"WARNING: weak Maharashtra data for: {weak_crops}")

    # --- c) LEAKAGE 1: Yield vs Production/Area ------------------------------
    lines.append("\n## c) Leakage check 1: Yield vs Production/Area\n")
    diff = leakage_yield_vs_production(df)
    max_diff = diff.max()
    mean_diff = diff.mean()
    lines.append(f"- Rows compared (Area > 0): {len(diff)}\n")
    lines.append(f"- max abs diff |Yield - Production/Area|: {max_diff:.6g}\n")
    lines.append(f"- mean abs diff: {mean_diff:.6g}\n")
    leak1 = max_diff < 1e-6
    if leak1:
        lines.append(
            "- **Yield is (near-)exactly Production/Area -> Production is derived from "
            "Yield and must be dropped to avoid leakage.**\n"
        )
    else:
        lines.append(
            "- Yield is not exactly Production/Area; Production is still dropped from the "
            "cleaned frame as a conservative leakage precaution (Yield is the modeling target).\n"
        )
    print(f"Leakage 1: max abs diff = {max_diff:.6g} (near-zero => {leak1})")

    # --- d) LEAKAGE 2: Fertilizer/Pesticide totals vs Area -------------------
    lines.append("\n## d) Leakage check 2: Fertilizer/Pesticide vs Area\n")
    corr = correlation_fert_pesticide_area(df)
    lines.append(f"- corr(Fertilizer, Area) = {corr['fertilizer_vs_area']:.4f}\n")
    lines.append(f"- corr(Pesticide, Area) = {corr['pesticide_vs_area']:.4f}\n")
    leak2 = corr["fertilizer_vs_area"] > 0.8 and corr["pesticide_vs_area"] > 0.8
    if leak2:
        lines.append(
            "- **Both correlations > 0.8 -> Fertilizer/Pesticide are farm-level totals, "
            "not per-hectare rates. Converted to `fertilizer_per_ha`/`pesticide_per_ha` "
            "and raw totals dropped.**\n"
        )
    else:
        lines.append(
            "- Correlations below the 0.8 totals threshold; converting to per-hectare "
            "rates anyway for consistency with the modeling design.\n"
        )
    print(f"Leakage 2: corr(fert,area)={corr['fertilizer_vs_area']:.4f}, "
          f"corr(pest,area)={corr['pesticide_vs_area']:.4f} (totals => {leak2})")

    # --- e) outliers, invalid areas, duplicates -------------------------------
    lines.append("\n## e) Data quality: outliers, invalid areas, duplicates\n")

    outliers = find_outliers_iqr(df, crop_col="Crop", value_col="Yield")
    lines.append("\n### Per-crop yield outliers (IQR, 1.5x whiskers)\n")
    lines.append("\n| crop | n | n_outliers | lower_bound | upper_bound |\n|---|---|---|---|---|\n")
    for _, row in outliers.iterrows():
        lines.append(
            f"| {row['crop']} | {row['n']} | {row['n_outliers']} | "
            f"{row['lower_bound']:.4g} | {row['upper_bound']:.4g} |\n"
        )

    invalid_areas = find_invalid_areas(df)
    lines.append(f"\n### Zero/negative areas\n- {len(invalid_areas)} rows with Area <= 0 "
                  f"(dropped from the cleaned frame; per-hectare rates are undefined otherwise).\n")

    dupes = find_duplicates(df)
    lines.append(f"\n### Duplicates\n- {len(dupes)} rows involved in exact duplicates "
                  f"(kept once in the cleaned frame).\n")
    print(f"Data quality: {len(invalid_areas)} invalid-area rows, {len(dupes)} duplicate rows.")

    # --- f) plots --------------------------------------------------------------
    lines.append("\n## f) Plots\n")

    mh = df[df["State"] == STATE].copy()
    target_yield_names = {v["yield"]: k for k, v in CROP_NAME_MAP.items()}
    mh_target = mh[mh["Crop"].isin(target_yield_names)].copy()
    mh_target["canon_crop"] = mh_target["Crop"].map(target_yield_names)

    if not mh_target.empty:
        fig, ax = plt.subplots(figsize=(10, 6))
        mh_target.boxplot(column="Yield", by="canon_crop", ax=ax, rot=45)
        ax.set_title(f"{STATE} yield distribution per target crop")
        ax.set_xlabel("crop")
        ax.set_ylabel("Yield (t/ha)")
        plt.suptitle("")
        fig.tight_layout()
        fig.savefig(REPORTS_EDA / "yield_distribution_by_crop.png", dpi=150)
        plt.close(fig)
        lines.append("- `yield_distribution_by_crop.png`\n")

        fig, ax = plt.subplots(figsize=(10, 6))
        for crop, sub in mh_target.groupby("canon_crop"):
            yearly = sub.groupby("Crop_Year")["Yield"].mean()
            ax.plot(yearly.index, yearly.values, marker="o", label=crop)
        ax.set_title(f"{STATE} mean yield over years per target crop")
        ax.set_xlabel("year")
        ax.set_ylabel("Yield (t/ha)")
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(REPORTS_EDA / "yield_over_years_by_crop.png", dpi=150)
        plt.close(fig)
        lines.append("- `yield_over_years_by_crop.png`\n")
    else:
        lines.append(f"- No {STATE} rows for target crops; distribution/trend plots skipped.\n")

    clean_all = clean_yield_data(df)
    numeric_cols = ["area_ha", "rainfall_mm", "fertilizer_per_ha", "pesticide_per_ha", "yield"]
    corr_matrix = clean_all[numeric_cols].corr()
    fig, ax = plt.subplots(figsize=(7, 6))
    im = ax.imshow(corr_matrix.values, cmap="coolwarm", vmin=-1, vmax=1)
    ax.set_xticks(range(len(numeric_cols)))
    ax.set_yticks(range(len(numeric_cols)))
    ax.set_xticklabels(numeric_cols, rotation=45, ha="right")
    ax.set_yticklabels(numeric_cols)
    for i in range(len(numeric_cols)):
        for j in range(len(numeric_cols)):
            ax.text(j, i, f"{corr_matrix.values[i, j]:.2f}", ha="center", va="center", fontsize=8)
    ax.set_title("Correlation heatmap (post per-ha conversion)")
    fig.colorbar(im, ax=ax, shrink=0.8)
    fig.tight_layout()
    fig.savefig(REPORTS_EDA / "correlation_heatmap.png", dpi=150)
    plt.close(fig)
    lines.append("- `correlation_heatmap.png`\n")

    # --- save cleaned ALL-INDIA frame ------------------------------------------
    clean_all.to_parquet(YIELD_CLEAN_PARQUET, index=False)
    print(f"Wrote cleaned yield frame: {YIELD_CLEAN_PARQUET} ({len(clean_all)} rows)")
    lines.append(f"\n## Cleaned output\n- `{YIELD_CLEAN_PARQUET}`: {len(clean_all)} rows "
                  f"(all-India, `Production` dropped, per-hectare rates, `is_target_crop` flag).\n")

    report_path = REPORTS_EDA / "eda_report.md"
    report_path.write_text("".join(lines), encoding="utf-8")
    print(f"Wrote report: {report_path}")


if __name__ == "__main__":
    sys.exit(main())
