"""
QuantLib定价模块 - 天气衍生品的Black-Scholes定价和希腊值计算
将天气指数转化为可交易资产进行期权定价
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
from datetime import datetime, timedelta

try:
    import QuantLib as ql
    HAS_QUANTLIB = True
except ImportError:
    HAS_QUANTLIB = False
    print("Warning: QuantLib not available. Using fallback pricing methods.")


class QuantLibPricer:
    """使用QuantLib进行天气衍生品定价"""

    def __init__(self):
        if not HAS_QUANTLIB:
            raise ImportError("QuantLib is required for this module")

    def setup_calendar(self, calendar_type: str = 'China'):
        calendars = {
            'China': ql.China(),
            'US': ql.UnitedStates(ql.UnitedStates.NYSE),
            'UK': ql.UnitedKingdom(),
            'Japan': ql.Japan(),
            'TARGET': ql.TARGET()
        }
        return calendars.get(calendar_type, ql.NullCalendar())

    def create_weather_option_ql(self,
                                 option_type: str,
                                 strike: float,
                                 spot: float,
                                 sigma: float,
                                 risk_free_rate: float,
                                 dividend_yield: float,
                                 start_date: str,
                                 end_date: str,
                                 calendar: str = 'China',
                                 day_count: str = 'Actual365Fixed') -> Dict:
        if not HAS_QUANTLIB:
            return self._fallback_pricing(
                option_type, strike, spot, sigma,
                risk_free_rate, dividend_yield,
                start_date, end_date
            )

        cal = self.setup_calendar(calendar)

        if day_count == 'Actual365Fixed':
            dc = ql.Actual365Fixed()
        elif day_count == 'Actual360':
            dc = ql.Actual360()
        else:
            dc = ql.Actual365Fixed()

        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        settlement_days = 0

        spot_date = ql.Date(start.day, start.month, start.year)
        maturity_date = ql.Date(end.day, end.month, end.year)

        ql.Settings.instance().evaluationDate = spot_date

        if option_type == 'call':
            option_type_ql = ql.Option.Call
        else:
            option_type_ql = ql.Option.Put

        payoff = ql.PlainVanillaPayoff(option_type_ql, strike)
        exercise = ql.EuropeanExercise(maturity_date)
        european_option = ql.VanillaOption(payoff, exercise)

        spot_handle = ql.QuoteHandle(ql.SimpleQuote(spot))
        flat_ts = ql.YieldTermStructureHandle(
            ql.FlatForward(settlement_days, cal, risk_free_rate, dc)
        )
        dividend_yield_ts = ql.YieldTermStructureHandle(
            ql.FlatForward(settlement_days, cal, dividend_yield, dc)
        )
        flat_vol_ts = ql.BlackVolTermStructureHandle(
            ql.BlackConstantVol(settlement_days, cal, sigma, dc)
        )

        bsm_process = ql.BlackScholesMertonProcess(
            spot_handle, dividend_yield_ts, flat_ts, flat_vol_ts
        )

        engine = ql.AnalyticEuropeanEngine(bsm_process)
        european_option.setPricingEngine(engine)

        try:
            npv = european_option.NPV()
            delta = european_option.delta()
            gamma = european_option.gamma()
            vega = european_option.vega()
            theta = european_option.theta()
            rho = european_option.rho()
            itm_cash_prob = european_option.itmCashProbability()

            return {
                'price': npv,
                'delta': delta,
                'gamma': gamma,
                'vega': vega,
                'theta': theta,
                'rho': rho,
                'itm_probability': itm_cash_prob,
                'strike': strike,
                'spot': spot,
                'volatility': sigma,
                'risk_free_rate': risk_free_rate
            }
        except Exception as e:
            return {'error': str(e)}

    def _fallback_pricing(self,
                          option_type: str,
                          strike: float,
                          spot: float,
                          sigma: float,
                          risk_free_rate: float,
                          dividend_yield: float,
                          start_date: str,
                          end_date: str) -> Dict:
        from scipy.stats import norm

        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        T = (end - start).days / 365.0

        d1 = (np.log(spot/strike) + (risk_free_rate - dividend_yield + 0.5*sigma**2)*T) / (sigma*np.sqrt(T))
        d2 = d1 - sigma*np.sqrt(T)

        if option_type == 'call':
            price = spot*np.exp(-dividend_yield*T)*norm.cdf(d1) - strike*np.exp(-risk_free_rate*T)*norm.cdf(d2)
            delta = norm.cdf(d1)
        else:
            price = strike*np.exp(-risk_free_rate*T)*norm.cdf(-d2) - spot*np.exp(-dividend_yield*T)*norm.cdf(-d1)
            delta = norm.cdf(d1) - 1

        gamma = norm.pdf(d1) / (spot*sigma*np.sqrt(T))
        vega = spot*norm.pdf(d1)*np.sqrt(T)
        rho = strike*T*np.exp(-risk_free_rate*T)*norm.cdf(d2) if option_type == 'call' else \
              -strike*T*np.exp(-risk_free_rate*T)*norm.cdf(-d2)
        theta = -spot*norm.pdf(d1)*sigma/(2*np.sqrt(T)) - \
                risk_free_rate*strike*np.exp(-risk_free_rate*T)*norm.cdf(d2) if option_type == 'call' else \
                -spot*norm.pdf(d1)*sigma/(2*np.sqrt(T)) + \
                risk_free_rate*strike*np.exp(-risk_free_rate*T)*norm.cdf(-d2)

        return {
            'price': price,
            'delta': delta,
            'gamma': gamma,
            'vega': vega,
            'theta': theta,
            'rho': rho,
            'itm_probability': norm.cdf(d2) if option_type == 'call' else norm.cdf(-d2),
            'strike': strike,
            'spot': spot,
            'volatility': sigma,
            'risk_free_rate': risk_free_rate,
            'method': 'Black-Scholes (fallback)'
        }

    def price_weather_derivative(self,
                                 contract_type: str,
                                 strike: float,
                                 index_value: float,
                                 volatility: float,
                                 risk_free_rate: float,
                                 tick_size: float,
                                 start_date: str,
                                 end_date: str,
                                 calendar: str = 'China') -> Dict:
        is_call = 'call' in contract_type.lower()
        option_type = 'call' if is_call else 'put'

        result = self.create_weather_option_ql(
            option_type=option_type,
            strike=strike,
            spot=index_value,
            sigma=volatility,
            risk_free_rate=risk_free_rate,
            dividend_yield=0.0,
            start_date=start_date,
            end_date=end_date,
            calendar=calendar
        )

        if 'error' not in result:
            result['price_per_unit'] = result['price']
            result['contract_value'] = result['price'] * tick_size
            result['method'] = 'QuantLib Analytic European'

        return result

    def generate_greeks_surface(self,
                                option_type: str,
                                spot_range: Tuple[float, float],
                                vol_range: Tuple[float, float],
                                strike: float,
                                risk_free_rate: float,
                                start_date: str,
                                end_date: str,
                                n_points: int = 20) -> Dict:
        spots = np.linspace(spot_range[0], spot_range[1], n_points)
        vols = np.linspace(vol_range[0], vol_range[1], n_points)

        delta_surface = np.zeros((n_points, n_points))
        gamma_surface = np.zeros((n_points, n_points))
        price_surface = np.zeros((n_points, n_points))

        for i, spot in enumerate(spots):
            for j, vol in enumerate(vols):
                result = self.create_weather_option_ql(
                    option_type=option_type,
                    strike=strike,
                    spot=spot,
                    sigma=vol,
                    risk_free_rate=risk_free_rate,
                    dividend_yield=0.0,
                    start_date=start_date,
                    end_date=end_date
                )
                if 'error' not in result:
                    delta_surface[i, j] = result['delta']
                    gamma_surface[i, j] = result['gamma']
                    price_surface[i, j] = result['price']

        return {
            'spots': spots,
            'volatilities': vols,
            'delta_surface': delta_surface,
            'gamma_surface': gamma_surface,
            'price_surface': price_surface
        }

    def calculate_implied_volatility(self,
                                     market_price: float,
                                     option_type: str,
                                     strike: float,
                                     spot: float,
                                     risk_free_rate: float,
                                     start_date: str,
                                     end_date: str) -> Optional[float]:
        if not HAS_QUANTLIB:
            return self._bs_implied_vol(
                market_price, option_type, strike, spot,
                risk_free_rate, start_date, end_date
            )

        try:
            cal = self.setup_calendar('China')
            dc = ql.Actual365Fixed()

            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')

            spot_date = ql.Date(start.day, start.month, start.year)
            maturity_date = ql.Date(end.day, end.month, end.year)
            ql.Settings.instance().evaluationDate = spot_date

            if option_type == 'call':
                opt_type = ql.Option.Call
            else:
                opt_type = ql.Option.Put

            payoff = ql.PlainVanillaPayoff(opt_type, strike)
            exercise = ql.EuropeanExercise(maturity_date)
            option = ql.VanillaOption(payoff, exercise)

            spot_handle = ql.QuoteHandle(ql.SimpleQuote(spot))
            flat_ts = ql.YieldTermStructureHandle(
                ql.FlatForward(0, cal, risk_free_rate, dc)
            )
            dividend_ts = ql.YieldTermStructureHandle(
                ql.FlatForward(0, cal, 0.0, dc)
            )

            price_quote = ql.SimpleQuote(market_price)
            vol = option.impliedVolatility(
                price_quote.value(),
                ql.BlackScholesMertonProcess(spot_handle, dividend_ts, flat_ts,
                                             ql.BlackVolTermStructureHandle(
                                                 ql.BlackConstantVol(0, cal, 0.2, dc)
                                             ))
            )
            return vol
        except Exception as e:
            return None

    def _bs_implied_vol(self,
                        market_price: float,
                        option_type: str,
                        strike: float,
                        spot: float,
                        risk_free_rate: float,
                        start_date: str,
                        end_date: str) -> Optional[float]:
        from scipy.stats import norm
        from scipy.optimize import brentq

        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        T = (end - start).days / 365.0

        def bs_price(sigma):
            d1 = (np.log(spot/strike) + (risk_free_rate + 0.5*sigma**2)*T) / (sigma*np.sqrt(T))
            d2 = d1 - sigma*np.sqrt(T)
            if option_type == 'call':
                return spot*norm.cdf(d1) - strike*np.exp(-risk_free_rate*T)*norm.cdf(d2)
            else:
                return strike*np.exp(-risk_free_rate*T)*norm.cdf(-d2) - spot*norm.cdf(-d1)

        try:
            implied_vol = brentq(lambda x: bs_price(x) - market_price, 0.001, 5.0)
            return implied_vol
        except ValueError:
            return None
