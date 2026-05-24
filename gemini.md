# Gemini Execution Log

## Task Summary
1. Downloaded and decompressed the snapshot data:
   - Compressed archive downloaded: `gg_stock_data_20260523.tar.gz`
   - Archive decompressed. Database file: `sql/stock_data.db` and stock data files: `data/stock_data/` are updated.
2. Troubleshot and fixed two Pandas version compatibility bugs (Pandas 2.0+):
   - **Bug 1**: `NDFrame.fillna()` no longer supports the `method` argument.
     - Files modified: `stock_comm.py`, `twii.py`, `kline.py`, `all_stock.py`.
     - Action: Replaced `.fillna(method='ffill')` with `.ffill()`.
   - **Bug 2**: `TypeError: Invalid value '2026-05-22 00:00:00' for dtype 'float64'` in `gg_stock.py`.
     - Location: `gg_stock.py` line 532 (`d.at[0,'date']=date`).
     - Cause: Column `date` was initialized as `np.nan` (float64) and not cast to string/object before assignment.
     - Action: Cast `date` column to `'object'` type in `gg_stock.py` (line 530) so that it can hold `pandas.Timestamp` values without type errors.
3. Troubleshot and fixed additional Pandas 2.0+ TypeError bugs during script run:
   - **Bug 3**: `TypeError: Invalid value '2024-05-21' for dtype 'float64'` in `stock_comm.py` (line 491: `outdf.loc[0] = df.loc[0]`).
     - Cause: `outdf` was initialized with `np.nan` (float64), and assigning a string date row from `df.loc[0]` crashed.
     - Action: Cast `'date'` column in `outdf` to `'object'` type in `stock_comm.py` immediately after initializing `outdf`.
   - **Bug 4**: Anticipated type crash in `revenue.py` during transposition.
     - Cause: `d` was initialized as `float64` via `np.nan`, and assigning mixed type list values via `d.iloc[i-1] = ...` would trigger `TypeError`.
     - Action: Cast the entire DataFrame `d` to `'object'` type in `revenue.py` (line 558) before assigning lists of mixed types to rows.
   - **Bug 5**: `TypeError: float() argument must be a string or a real number, not 'NoneType'` in `stock_comm.py`.
     - Location: `stock_comm.py` line 1097 (`float(x)` inside `tofloat64`).
     - Cause: A `None` value (null in SQL database) was passed to `tofloat64` when processing `營業毛利（毛損）淨額`.
     - Action: Updated `tofloat64(x)` to safely check for `None` or `NaN` (using `pd.isna`) and return `np.nan`, and added exception handling for conversion.
   - **Bug 6**: `TypeError: unsupported operand type(s) for /: 'NoneType' and 'float'` in `gg_stock.py`.
     - Location: `gg_stock.py` line 325 (`df.iloc[i]['單季營業利益淨額']/df.iloc[i]['單季營收']`).
     - Cause: `None` values (null in SQL database) for financial numbers caused Division operations to fail.
     - Action: Defined a robust helper function `calc_ratio(num, den)` that handles `None`, `NaN`, and zero-division errors, and used it for all margin division computations.
4. Created Web Control Dashboard:
   - Revamped `online.py` to fix critical undefined variables and name errors.
   - Integrated subprocess execution runner with thread controls for `crawl.py`, `download_snapshot.py`, and `gg_stock.py`.
   - Created beautiful glassmorphic templates: `online.html`, `top.html`, `kline.html` inside `templates/`.
   - Added live console terminal monitor to view execution logs dynamically via AJAX polling.
   - Enabled direct static links to view generated HTML stock picking reports in the browser.
   - Added buttons to manually execute specialized crawlers: `tdcc_get.py` (TDCC), `revenue.py` (Revenue), `director.py` (Director), and `eps.py` (EPS).
   - Embedded recommended update schedules directly in the web dashboard for each button.
5. 除非要求，不然一律回中文。


## Commands to Run
To run the web console:
```bash
.\venv\Scripts\python.exe online.py
```
And open your browser at: `http://127.0.0.1:5000/online/`
