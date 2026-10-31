import numpy as np
from typing import List, Dict, Any
import math

class StatisticalForecasting:
    @staticmethod
    def simple_moving_average(history: List[float], window: int = 3, horizon: int = 30) -> List[float]:
        """
        Computes rolling SMA and extends it forward.
        """
        if not history:
            return [0.0] * horizon
        if len(history) < window:
            window = len(history)
            
        recent = history[-window:]
        avg = float(np.mean(recent))
        return [round(avg, 2) for _ in range(horizon)]

    @staticmethod
    def holts_linear_trend(history: List[float], alpha: float = 0.3, beta: float = 0.1, horizon: int = 30) -> List[float]:
        """
        Double Exponential Smoothing (Holt's Linear Trend Model):
        Level:  L_t = alpha * Y_t + (1 - alpha) * (L_{t-1} + T_{t-1})
        Trend:  T_t = beta * (L_t - L_{t-1}) + (1 - beta) * T_{t-1}
        Forecast: F_{t+m} = L_t + m * T_t
        """
        n = len(history)
        if n < 2:
            val = history[0] if n == 1 else 10.0
            return [round(val, 2) for _ in range(horizon)]

        # Initial level and trend
        level = history[0]
        trend = history[1] - history[0]

        for t in range(1, n):
            val = history[t]
            prev_level = level
            level = alpha * val + (1.0 - alpha) * (prev_level + trend)
            trend = beta * (level - prev_level) + (1.0 - beta) * trend

        # Generate predictions for m steps ahead
        forecast = []
        for m in range(1, horizon + 1):
            pred = max(0.0, level + m * trend)
            forecast.append(round(pred, 2))
        return forecast

    @classmethod
    def generate_material_requirement_forecast(
        cls,
        item_id: str,
        historical_consumption: List[float],
        lead_time_days: int = 5,
        service_level_z: float = 1.65, # 95% service level
        horizon: int = 30,
        method: str = "holt_winters"
    ) -> Dict[str, Any]:
        """
        Estimates future material consumption and computes statistically rigorous
        Safety Stock and Dynamic Reorder Point based on historical demand variability and supplier lead time.
        """
        if not historical_consumption:
            historical_consumption = [20.0, 22.0, 19.0, 25.0, 24.0, 28.0, 26.0, 30.0]

        data = np.array(historical_consumption, dtype=float)
        mean_demand = float(np.mean(data))
        std_demand = float(np.std(data, ddof=1)) if len(data) > 1 else (mean_demand * 0.15)

        # 1. Generate future point forecasts
        if method == "sma":
            forecast_values = cls.simple_moving_average(historical_consumption, window=3, horizon=horizon)
        else:
            forecast_values = cls.holt_winters_or_linear(historical_consumption, horizon=horizon)

        projected_daily = float(np.mean(forecast_values))

        # 2. Statistical Safety Stock:
        # SS = Z * sigma_L = Z * (sigma_d * sqrt(LeadTime))
        lead_time_factor = math.sqrt(max(1, lead_time_days))
        sigma_lead_time = std_demand * lead_time_factor
        safety_stock = round(service_level_z * sigma_lead_time, 2)

        # 3. Dynamic ROP:
        # ROP = (Projected Daily Demand * Lead Time) + Safety Stock
        dynamic_rop = round((projected_daily * lead_time_days) + safety_stock, 2)

        # 4. 95% Confidence Bounds
        upper_bound = [round(v + (1.96 * std_demand), 2) for v in forecast_values]
        lower_bound = [round(max(0.0, v - (1.96 * std_demand)), 2) for v in forecast_values]

        return {
            "itemId": item_id,
            "method_used": method,
            "forecast_values": forecast_values,
            "projected_daily_demand": round(projected_daily, 2),
            "historical_mean": round(mean_demand, 2),
            "historical_std_dev": round(std_demand, 2),
            "lead_time_days": lead_time_days,
            "safety_stock_recommended": safety_stock,
            "reorder_point_calculated": dynamic_rop,
            "confidence_interval_95": {
                "upper": upper_bound,
                "lower": lower_bound
            }
        }

    @classmethod
    def holt_winters_or_linear(cls, history: List[float], horizon: int = 30) -> List[float]:
        try:
            from statsmodels.tsa.holtwinters import ExponentialSmoothing
            if len(history) >= 8:
                model = ExponentialSmoothing(history, trend="add", seasonal=None, initialization_method="estimated")
                fitted = model.fit()
                preds = fitted.forecast(horizon)
                return [round(max(0.0, float(x)), 2) for x in preds]
        except Exception:
            pass
        return cls.holts_linear_trend(history, horizon=horizon)

forecaster = StatisticalForecasting()

