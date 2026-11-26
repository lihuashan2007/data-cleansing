# Data Cleansing

Python helpers for reshaping pandas DataFrames, cleaning names, working with calendar dates, and preparing WRDS event returns. Requires Python 3.10 or later and pandas 2.2 through 3.x.

## Install

Run this in the Python environment for your project. In a Jupyter notebook, use `%pip install` with the same requirement in that notebook’s kernel.

```bash
python -m pip install "data-cleansing @ git+https://github.com/lihuashan2007/data-cleansing.git@v0.1.0"
```

```python
import pandas as pd
import data_cleansing as dc

companies = pd.DataFrame({
    "legal_name": ["Example Motors", None],
    "display_name": ["Example", "Sample Parts"],
})
cleaned = dc.combine_cols(companies, "legal_name", "display_name", "company")
assert cleaned["company"].tolist() == ["Example Motors", "Sample Parts"]
assert dc.date_back("20240331", 1) == "20240229"
```

Existing notebooks can use `import DataCleansing as dc`. If you previously kept a copy of `DataCleansing.py` alongside a notebook, use `print(dc.__file__)` to see which copy Python loaded. Switch the import to `data_cleansing` or move the old copy out of the notebook’s import path to use the installed package. Restart the kernel after updating.

## Helpers

| Module | Examples |
| --- | --- |
| `data_cleansing.frames` | `extend_df_list`, `combine_cols`, `detect_duplicate`, `group_rolling` |
| `data_cleansing.text` | `clean_car_model`, `clean_province`, `find_content_in_bracket` |
| `data_cleansing.dates` | `date_to_quarter`, `date_back`, `change_time_zone` |
| `data_cleansing.industry` | `valid_obs`, `identify_manufacturing`, `valid_industry` |
| `data_cleansing.wrds` | `find_r_date`, `WRDS_CAR_data`, `WRDS_event_data_transform_revised` |

All 46 functions are also available at the package root. Use `help(dc.group_month_rolling)` for a function’s inputs and return value.

## Changes from the original script

- DataFrame inputs are treated as read-only. Use the returned DataFrame from functions such as `combine_cols`, `assign_id`, and `detect_duplicate`. `combine_cols` falls back on nulls and the literal `"NOT AVAILABLE"`. Duplicate checks now return empty DataFrames with their result columns when there are no matches. `assign_id` leaves null keys missing. Group percentage changes use the previous row’s value without filling gaps.
- List expansion keeps the original row labels, omits empty lists, and checks paired list lengths within each row. Missing list cells count as empty, and `list_exclude_by_list` preserves first-seen order.
- Date shifts support offsets spanning several years and clamp month-end dates. `change_time_zone` converts to New York local time using daylight-saving rules. For example, `2024-07-08 04:30:00` UTC now gives `20240708`. The fiscal year starts in June, annual rolling sums cover years `year - 5` through `year - 1`, and monthly sums use strict bounds between the shifted cutoff and the row date.
- WRDS reshaping retains the original event windows and column names. It collapses identical records within an event day and raises `ValueError` for conflicting records under the same event-day key.
- Text helpers handle pandas missing values where they previously only checked for floats. Diagnostic output uses Python logging at the `DEBUG` level.

## Develop and update

```bash
git clone https://github.com/lihuashan2007/data-cleansing.git
cd data-cleansing
python -m pip install -e .
python -m unittest discover -s tests -v
```

GitHub Actions tests the package on pandas 2.2 and 3.x. To release an update, bump the version in `pyproject.toml`, run the tests, push the commit, and publish the matching GitHub tag. In a consuming project, update the tag in the install command or dependency file and reinstall with `--upgrade`. For a paper replication, pin the full Git commit and lock the Python environment dependencies as well.
