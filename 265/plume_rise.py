import numpy as np

class HeatSourceModel:
    def __init__(self, v_s, d, T_s, T_a=293.0, P=101325.0):
        self.v_s = v_s
        self.d = d
        self.T_s = T_s
        self.T_a = T_a
        self.P = P

        self.g = 9.81
        self.c_p = 1005.0
        self.R_gas = 287.0

        self.calculate_heat_source_params()

    def calculate_heat_source_params(self):
        self.rho_s = self.P / (self.R_gas * self.T_s)
        self.rho_a = self.P / (self.R_gas * self.T_a)

        self.beta = self.T_s - self.T_a

        self.w_star = self.v_s * np.sqrt(self.rho_s / self.rho_a)

        self.Q_mass = self.rho_s * self.v_s * np.pi * (self.d / 2) ** 2

        if self.beta > 0:
            self.F_b = self.g * self.beta * self.w_star * (self.d / 2) ** 2
            self.Qh = self.c_p * self.Q_mass * self.beta
        else:
            self.F_b = 0.0
            self.Qh = 0.0

        self.M = self.rho_s * self.v_s ** 2 * np.pi * (self.d / 2) ** 2

        self.F_r = self.F_b / (self.w_star ** 3 * self.d) if self.w_star > 0 and self.d > 0 else 0.0

        self.R_i = self.g * self.beta * self.d / (self.T_a * self.w_star ** 2) if self.w_star > 0 else 0.0

        if self.beta >= 0:
            self.l_m = (self.w_star ** 2 * self.d) / (2 * self.g * self.beta / self.T_a) if self.beta > 0 else np.inf
        else:
            self.l_m = np.inf

        return {
            'rho_s': self.rho_s,
            'rho_a': self.rho_a,
            'beta': self.beta,
            'w_star': self.w_star,
            'F_b': self.F_b,
            'Qh': self.Qh,
            'M': self.M,
            'F_r': self.F_r,
            'R_i': self.R_i,
            'l_m': self.l_m
        }

    def get_plume_regime(self, x, u, stability_class):
        x = np.asarray(x, dtype=float)

        x_m = 3.5 * self.l_m

        if self.F_b > 0:
            if stability_class in ['A', 'B', 'C']:
                x_star = 14 * self.F_b ** (5/8)
            elif stability_class == 'D':
                x_star = 34 * self.F_b ** (2/3)
            else:
                x_star = 4 * self.F_b ** (1/2)
        else:
            x_star = np.inf

        regime = np.where(x < x_m, 'momentum',
                         np.where(x < x_star, 'bouyant_near', 'bouyant_far'))

        return regime, x_m, x_star

    def correct_temperature_effect(self, delta_h_base, x):
        x = np.asarray(x, dtype=float)

        if self.beta > 50:
            temp_correction = 1.0 + 0.3 * np.tanh(self.beta / 100)
        elif self.beta > 0:
            temp_correction = 1.0 + 0.1 * np.tanh(self.beta / 50)
        elif self.beta < -20:
            temp_correction = 0.7 + 0.3 * np.exp(self.beta / 50)
        else:
            temp_correction = 1.0

        return delta_h_base * temp_correction

    def correct_velocity_effect(self, delta_h_base, x, u):
        x = np.asarray(x, dtype=float)

        velocity_ratio = self.w_star / u if u > 0 else 10.0

        if velocity_ratio > 5:
            vel_correction = 1.0 + 0.2 * np.tanh((velocity_ratio - 5) / 5)
        elif velocity_ratio > 1:
            vel_correction = 1.0
        else:
            vel_correction = 0.6 + 0.4 * np.tanh(velocity_ratio)

        return delta_h_base * vel_correction

    def calculate_heat_source_correction(self, delta_h_base, x, u, stability_class):
        x = np.asarray(x, dtype=float)

        temp_corrected = self.correct_temperature_effect(delta_h_base, x)
        vel_corrected = self.correct_velocity_effect(temp_corrected, x, u)

        stability_factor = 1.0
        if stability_class in ['A', 'B', 'C']:
            stability_factor = 1.1
        elif stability_class in ['E', 'F']:
            stability_factor = 0.9

        return vel_corrected * stability_factor

def calculate_bouyant_plume_rise_advanced(x, heat_source, u, stability_class):
    x = np.asarray(x, dtype=float)
    x = np.maximum(x, 1.0)

    F_b = heat_source.F_b

    if F_b <= 0:
        return np.zeros_like(x)

    if stability_class in ['A', 'B', 'C']:
        x_star = 14 * F_b ** (5/8)
        delta_h_near = 1.6 * F_b ** (1/3) * x ** (2/3) / u
        delta_h_far = 1.6 * F_b ** (1/3) * x_star ** (2/3) / u
        delta_h = np.where(x < x_star, delta_h_near, delta_h_far)
    elif stability_class == 'D':
        x_star = 34 * F_b ** (2/3)
        delta_h_near = 1.6 * F_b ** (1/3) * x ** (2/3) / u
        delta_h_far = 1.6 * F_b ** (1/3) * x_star ** (2/3) / u
        delta_h = np.where(x < x_star, delta_h_near, delta_h_far)
    else:
        x_star = 4 * F_b ** (1/2)
        delta_h_near = 1.6 * F_b ** (1/3) * x ** (2/3) / u
        delta_h_far = 2.4 * (F_b / u) ** (1/3) * np.log(x / x_star) + 1.6 * F_b ** (1/3) * x_star ** (2/3) / u
        delta_h = np.where(x < x_star, delta_h_near, delta_h_far)

    delta_h = heat_source.calculate_heat_source_correction(delta_h, x, u, stability_class)

    return np.maximum(delta_h, 0)

def calculate_momentum_plume_rise_advanced(x, heat_source, u):
    x = np.asarray(x, dtype=float)
    x = np.maximum(x, 1.0)

    w_star = heat_source.w_star
    d = heat_source.d
    beta = heat_source.beta
    T_a = heat_source.T_a

    if beta >= 0:
        l_m = heat_source.l_m
    else:
        l_m = np.inf

    x_m = 3.5 * l_m

    delta_h = np.where(x < x_m,
                       1.5 * w_star * d / u,
                       3.0 * (w_star ** 2 * d * beta / T_a) ** (1/3) * x ** (1/3) / u)

    delta_h = heat_source.correct_velocity_effect(delta_h, x, u)

    return np.maximum(delta_h, 0)

def calculate_combined_plume_rise_advanced(x, v_s, d, T_s, T_a, u, stability_class):
    x = np.asarray(x, dtype=float)

    heat_source = HeatSourceModel(v_s, d, T_s, T_a)

    delta_h_bouyant = calculate_bouyant_plume_rise_advanced(x, heat_source, u, stability_class)
    delta_h_momentum = calculate_momentum_plume_rise_advanced(x, heat_source, u)

    delta_h = np.maximum(delta_h_bouyant, delta_h_momentum)

    return delta_h, heat_source

def calculate_effective_stack_height_advanced(x, h_s, v_s, d, T_s, T_a, u, stability_class):
    x = np.asarray(x, dtype=float)
    delta_h, heat_source = calculate_combined_plume_rise_advanced(
        x, v_s, d, T_s, T_a, u, stability_class
    )
    H_e = h_s + delta_h
    return H_e, delta_h, heat_source

def calculate_bouyant_plume_rise(x, Qh, T_s, T_a, u, stability_class):
    x = np.asarray(x, dtype=float)
    x = np.maximum(x, 1.0)

    g = 9.81
    F_b = g * Qh / (1005 * T_a)

    if stability_class in ['A', 'B', 'C']:
        x_star = 14 * F_b ** (5/8)
        delta_h_near = 1.6 * F_b ** (1/3) * x ** (2/3) / u
        delta_h_far = 1.6 * F_b ** (1/3) * x_star ** (2/3) / u
        delta_h = np.where(x < x_star, delta_h_near, delta_h_far)
    elif stability_class == 'D':
        x_star = 34 * F_b ** (2/3)
        delta_h_near = 1.6 * F_b ** (1/3) * x ** (2/3) / u
        delta_h_far = 1.6 * F_b ** (1/3) * x_star ** (2/3) / u
        delta_h = np.where(x < x_star, delta_h_near, delta_h_far)
    else:
        x_star = 4 * F_b ** (1/2)
        delta_h_near = 1.6 * F_b ** (1/3) * x ** (2/3) / u
        delta_h_far = 2.4 * (F_b / u) ** (1/3) * np.log(x / x_star) + 1.6 * F_b ** (1/3) * x_star ** (2/3) / u
        delta_h = np.where(x < x_star, delta_h_near, delta_h_far)

    return np.maximum(delta_h, 0)

def calculate_momentum_plume_rise(x, v_s, d, T_s, T_a, u):
    x = np.asarray(x, dtype=float)
    x = np.maximum(x, 1.0)

    beta = T_s - T_a
    rho_s = 353.1 / T_s
    rho_a = 353.1 / T_a
    w_star = v_s * np.sqrt(rho_s / rho_a)

    if beta >= 0:
        l_m = (w_star ** 2 * d) / (2 * 9.81 * beta / T_a) if beta > 0 else np.inf
    else:
        l_m = np.inf

    x_m = 3.5 * l_m

    delta_h = np.where(x < x_m,
                       1.5 * w_star * d / u,
                       3.0 * (w_star ** 2 * d * beta / T_a) ** (1/3) * x ** (1/3) / u)

    return np.maximum(delta_h, 0)

def calculate_combined_plume_rise(x, Qh, v_s, d, T_s, T_a, u, stability_class):
    x = np.asarray(x, dtype=float)

    delta_h_bouyant = calculate_bouyant_plume_rise(x, Qh, T_s, T_a, u, stability_class)
    delta_h_momentum = calculate_momentum_plume_rise(x, v_s, d, T_s, T_a, u)

    delta_h = np.maximum(delta_h_bouyant, delta_h_momentum)

    return delta_h

def calculate_effective_stack_height(x, h_s, Qh, v_s, d, T_s, T_a, u, stability_class):
    x = np.asarray(x, dtype=float)
    delta_h = calculate_combined_plume_rise(x, Qh, v_s, d, T_s, T_a, u, stability_class)
    H_e = h_s + delta_h
    return H_e, delta_h
