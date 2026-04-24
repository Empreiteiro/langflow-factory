from lfx.custom import Component
from lfx.io import (
    BoolInput,
    DataFrameInput,
    DropdownInput,
    IntInput,
    Output,
    StrInput,
)
from lfx.schema import Data, DataFrame
import pandas as pd


class TimeSeriesForecaster(Component):
    display_name = "Time Series Forecaster"
    description = (
        "Forecasts a univariate time series using ARIMA, Holt-Winters exponential smoothing "
        "or Prophet, and returns future values plus fit info."
    )
    icon = "mdi-trending-up"
    name = "TimeSeriesForecaster"

    inputs = [
        DataFrameInput(
            name="df",
            display_name="DataFrame",
            required=True,
        ),
        StrInput(
            name="date_column",
            display_name="Date Column",
            required=True,
        ),
        StrInput(
            name="value_column",
            display_name="Value Column",
            required=True,
        ),
        DropdownInput(
            name="model_type",
            display_name="Model",
            options=["arima", "holt_winters", "prophet"],
            value="arima",
            real_time_refresh=True,
        ),
        IntInput(name="horizon", display_name="Horizon", value=14),
        StrInput(
            name="freq",
            display_name="Frequency",
            info="Pandas frequency string (e.g. 'D', 'W', 'MS').",
            value="D",
        ),
        StrInput(
            name="arima_order",
            display_name="ARIMA Order",
            info="Comma-separated (p,d,q) values, e.g. '1,1,1'.",
            value="1,1,1",
        ),
        IntInput(
            name="seasonal_periods",
            display_name="Seasonal Periods",
            info="Seasonality length for Holt-Winters / Prophet yearly seasonality off).",
            value=0,
        ),
        BoolInput(
            name="holt_trend",
            display_name="Holt-Winters Trend",
            value=True,
        ),
    ]

    outputs = [
        Output(name="forecast", display_name="Forecast", method="get_forecast"),
        Output(name="report", display_name="Report", method="get_report"),
    ]

    def _prepare_series(self):
        if self.df is None:
            raise ValueError("No DataFrame provided.")
        if not self.date_column or not self.value_column:
            raise ValueError("date_column and value_column are required.")
        df = self.df.copy()
        df[self.date_column] = pd.to_datetime(df[self.date_column], errors="coerce")
        df = df.dropna(subset=[self.date_column, self.value_column]).sort_values(self.date_column)
        series = df.set_index(self.date_column)[self.value_column].astype(float)
        if self.freq:
            try:
                series = series.asfreq(self.freq)
            except Exception:
                pass
        series = series.interpolate().dropna()
        if series.empty:
            raise ValueError("Time series is empty after cleaning.")
        return series

    def _parse_order(self):
        parts = [p.strip() for p in (self.arima_order or "1,1,1").split(",") if p.strip()]
        if len(parts) != 3:
            raise ValueError("arima_order must have three comma-separated integers.")
        return tuple(int(p) for p in parts)

    def _run(self):
        series = self._prepare_series()
        horizon = int(self.horizon or 14)

        if self.model_type == "arima":
            try:
                from statsmodels.tsa.arima.model import ARIMA
            except ImportError as exc:
                raise ImportError("statsmodels is required for ARIMA.") from exc
            order = self._parse_order()
            model = ARIMA(series, order=order).fit()
            fc = model.forecast(steps=horizon)
            future_index = fc.index
            forecast_values = fc.values
            aic = float(model.aic)
            fit_info = {"order": order, "aic": aic}
        elif self.model_type == "holt_winters":
            try:
                from statsmodels.tsa.holtwinters import ExponentialSmoothing
            except ImportError as exc:
                raise ImportError("statsmodels is required for Holt-Winters.") from exc
            sp = int(self.seasonal_periods or 0)
            model = ExponentialSmoothing(
                series,
                trend="add" if self.holt_trend else None,
                seasonal="add" if sp > 1 else None,
                seasonal_periods=sp if sp > 1 else None,
            ).fit()
            fc = model.forecast(steps=horizon)
            future_index = fc.index
            forecast_values = fc.values
            fit_info = {"aic": float(getattr(model, "aic", float("nan")))}
        elif self.model_type == "prophet":
            try:
                from prophet import Prophet
            except ImportError as exc:
                raise ImportError("prophet is required. Install with: pip install prophet") from exc
            pdf = pd.DataFrame({"ds": series.index, "y": series.values})
            model = Prophet(yearly_seasonality=(int(self.seasonal_periods or 0) >= 365))
            model.fit(pdf)
            future = model.make_future_dataframe(periods=horizon, freq=self.freq or "D")
            forecast_df = model.predict(future).tail(horizon)
            future_index = pd.DatetimeIndex(forecast_df["ds"].values)
            forecast_values = forecast_df["yhat"].values
            fit_info = {"components": "yhat"}
        else:
            raise ValueError(f"Unsupported model: {self.model_type}")

        out = pd.DataFrame({
            self.date_column: future_index,
            f"{self.value_column}_forecast": forecast_values,
        })

        self._forecast = out
        self._report = {
            "model": self.model_type,
            "horizon": horizon,
            "freq": self.freq,
            "n_train": int(len(series)),
            "fit": fit_info,
        }
        self.log(f"TimeSeriesForecaster: {self._report}")

    def get_forecast(self) -> DataFrame:
        try:
            if not hasattr(self, "_forecast"):
                self._run()
            return DataFrame(self._forecast)
        except Exception as exc:
            self.log(f"TimeSeriesForecaster failed: {exc}")
            return DataFrame(pd.DataFrame({"error": [str(exc)]}))

    def get_report(self) -> Data:
        try:
            if not hasattr(self, "_report"):
                self._run()
            return Data(data=self._report)
        except Exception as exc:
            return Data(data={"error": str(exc)})
