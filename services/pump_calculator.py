from dataclasses import dataclass
from typing import Optional


# Втрати напору для труб ПНД на 100 м труби.
# Ключ першого рівня — витрата води, м³/год.
# Ключ другого рівня — діаметр труби, мм.
# Значення — втрати тиску, бар / 100 м.
HEAD_LOSS_TABLE_BAR_PER_100M: dict[float, dict[int, Optional[float]]] = {
    0.2: {20: 0.03, 25: 0.00, 32: 0.00, 40: 0.00, 50: 0.00, 63: 0.00, 75: 0.00},
    0.4: {20: 0.30, 25: 0.09, 32: 0.03, 40: 0.01, 50: 0.00, 63: 0.00, 75: 0.00},
    0.6: {20: 0.63, 25: 0.19, 32: 0.06, 40: 0.02, 50: 0.01, 63: 0.00, 75: 0.00},
    0.8: {20: 1.07, 25: 0.33, 32: 0.10, 40: 0.03, 50: 0.01, 63: 0.00, 75: 0.00},
    1.0: {20: 1.61, 25: 0.49, 32: 0.15, 40: 0.05, 50: 0.02, 63: 0.01, 75: 0.00},
    1.2: {20: 2.26, 25: 0.69, 32: 0.21, 40: 0.07, 50: 0.02, 63: 0.01, 75: 0.00},
    1.4: {20: 3.01, 25: 0.92, 32: 0.28, 40: 0.09, 50: 0.03, 63: 0.01, 75: 0.00},
    1.6: {20: 3.85, 25: 1.18, 32: 0.36, 40: 0.12, 50: 0.04, 63: 0.01, 75: 0.01},
    1.8: {20: 4.99, 25: 1.47, 32: 0.45, 40: 0.15, 50: 0.05, 63: 0.02, 75: 0.01},
    2.0: {20: 5.83, 25: 1.79, 32: 0.55, 40: 0.18, 50: 0.06, 63: 0.02, 75: 0.01},
    2.2: {20: 6.95, 25: 2.13, 32: 0.65, 40: 0.22, 50: 0.07, 63: 0.02, 75: 0.01},
    2.4: {20: 8.17, 25: 2.50, 32: 0.77, 40: 0.26, 50: 0.09, 63: 0.03, 75: 0.01},
    2.6: {20: 9.47, 25: 2.90, 32: 0.89, 40: 0.30, 50: 0.10, 63: 0.03, 75: 0.01},
    2.8: {20: 10.87, 25: 3.33, 32: 1.02, 40: 0.34, 50: 0.11, 63: 0.04, 75: 0.02},
    3.0: {20: 12.35, 25: 3.79, 32: 1.16, 40: 0.39, 50: 0.13, 63: 0.04, 75: 0.02},
    3.2: {20: 13.91, 25: 4.27, 32: 1.31, 40: 0.44, 50: 0.15, 63: 0.05, 75: 0.02},
    3.4: {20: 15.57, 25: 4.77, 32: 1.47, 40: 0.49, 50: 0.16, 63: 0.05, 75: 0.02},
    3.6: {20: 17.31, 25: 5.31, 32: 1.63, 40: 0.54, 50: 0.18, 63: 0.06, 75: 0.03},
    3.8: {20: None, 25: 5.86, 32: 1.80, 40: 0.60, 50: 0.20, 63: 0.07, 75: 0.03},
    4.0: {20: None, 25: 6.45, 32: 1.98, 40: 0.66, 50: 0.22, 63: 0.07, 75: 0.03},
    4.5: {20: None, 25: 8.02, 32: 2.46, 40: 0.82, 50: 0.28, 63: 0.09, 75: 0.04},
    5.0: {20: None, 25: 9.75, 32: 2.99, 40: 1.00, 50: 0.33, 63: 0.11, 75: 0.05},
    5.5: {20: None, 25: 11.63, 32: 3.57, 40: 1.19, 50: 0.40, 63: 0.13, 75: 0.06},
    6.0: {20: None, 25: 13.67, 32: 4.20, 40: 1.40, 50: 0.47, 63: 0.15, 75: 0.07},
    6.5: {20: None, 25: 15.85, 32: 4.87, 40: 1.62, 50: 0.54, 63: 0.18, 75: 0.08},
    7.0: {20: None, 25: None, 32: 5.59, 40: 1.86, 50: 0.62, 63: 0.20, 75: 0.09},
    7.5: {20: None, 25: None, 32: 6.35, 40: 2.17, 50: 0.71, 63: 0.23, 75: 0.10},
    8.0: {20: None, 25: None, 32: 7.15, 40: 2.38, 50: 0.80, 63: 0.26, 75: 0.11},
    8.5: {20: None, 25: None, 32: 8.00, 40: 2.66, 50: 0.89, 63: 0.29, 75: 0.12},
    9.0: {20: None, 25: None, 32: None, 40: 2.96, 50: 0.99, 63: 0.32, 75: 0.14},
    9.5: {20: None, 25: None, 32: None, 40: 3.27, 50: 1.10, 63: 0.36, 75: 0.15},
    10.0: {20: None, 25: None, 32: None, 40: 3.60, 50: 1.21, 63: 0.39, 75: 0.17},
    11.0: {20: None, 25: None, 32: None, 40: 4.29, 50: 1.44, 63: 0.47, 75: 0.20},
    12.0: {20: None, 25: None, 32: None, 40: 5.04, 50: 1.69, 63: 0.55, 75: 0.24},
    13.0: {20: None, 25: None, 32: None, 40: 5.85, 50: 1.96, 63: 0.64, 75: 0.27},
    14.0: {20: None, 25: None, 32: None, 40: 6.71, 50: 2.25, 63: 0.73, 75: 0.31},
    15.0: {20: None, 25: None, 32: None, 40: 7.62, 50: 2.56, 63: 0.83, 75: 0.36},
    16.0: {20: None, 25: None, 32: None, 40: 8.59, 50: 2.88, 63: 0.94, 75: 0.40},
    17.0: {20: None, 25: None, 32: None, 40: None, 50: 3.22, 63: 1.05, 75: 0.45},
    18.0: {20: None, 25: None, 32: None, 40: None, 50: 3.58, 63: 1.17, 75: 0.50},
    19.0: {20: None, 25: None, 32: None, 40: None, 50: 3.96, 63: 1.29, 75: 0.55},
    20.0: {20: None, 25: None, 32: None, 40: None, 50: None, 63: 1.42, 75: 0.61},
    22.0: {20: None, 25: None, 32: None, 40: None, 50: None, 63: 1.69, 75: 0.72},
    24.0: {20: None, 25: None, 32: None, 40: None, 50: None, 63: 1.99, 75: 0.85},
    26.0: {20: None, 25: None, 32: None, 40: None, 50: None, 63: 2.30, 75: 0.98},
    28.0: {20: None, 25: None, 32: None, 40: None, 50: None, 63: 2.64, 75: 1.13},
    30.0: {20: None, 25: None, 32: None, 40: None, 50: None, 63: 3.00, 75: 1.28},
    32.0: {20: None, 25: None, 32: None, 40: None, 50: None, 63: 3.38, 75: 1.45},
    34.0: {20: None, 25: None, 32: None, 40: None, 50: None, 63: 3.78, 75: 1.67},
    36.0: {20: None, 25: None, 32: None, 40: None, 50: None, 63: None, 75: 1.80},
    38.0: {20: None, 25: None, 32: None, 40: None, 50: None, 63: None, 75: 1.99},
    40.0: {20: None, 25: None, 32: None, 40: None, 50: None, 63: None, 75: 2.19},
}


@dataclass(frozen=True)
class IrrigationCalculation:
    total_tape_length_m: float
    total_emitters: float
    required_flow_l_h: float
    required_flow_m3_h: float


@dataclass(frozen=True)
class PumpRequirement:
    nearest_table_flow_m3_h: float
    pipe_loss_bar_per_100m: float
    total_pipe_loss_bar: float
    height_loss_bar: float
    drip_tape_pressure_bar: float
    filter_and_fittings_loss_bar: float
    required_pressure_bar: float
    required_pressure_with_reserve_bar: float
    required_head_m: float


def normalize_number(value: str) -> float:
    return float(value.strip().replace(",", "."))


def convert_area_to_m2(area: float, unit: str) -> float:
    if unit == "m2":
        return area
    if unit == "hundreds":
        return area * 100
    if unit == "ga":
        return area * 10_000
    raise ValueError("Невідома одиниця площі")


def calculate_irrigation_flow(
    area_m2: float,
    row_spacing_m: float,
    emitter_spacing_m: float,
    emitter_flow_l_h: float,
) -> IrrigationCalculation:
    if area_m2 <= 0:
        raise ValueError("Площа має бути більшою за 0")
    if row_spacing_m <= 0:
        raise ValueError("Відстань між рядками має бути більшою за 0")
    if emitter_spacing_m <= 0:
        raise ValueError("Крок емітера має бути більшим за 0")
    if emitter_flow_l_h <= 0:
        raise ValueError("Витрата емітера має бути більшою за 0")

    total_tape_length_m = area_m2 / row_spacing_m
    total_emitters = total_tape_length_m / emitter_spacing_m
    required_flow_l_h = total_emitters * emitter_flow_l_h
    required_flow_m3_h = required_flow_l_h / 1000

    return IrrigationCalculation(
        total_tape_length_m=total_tape_length_m,
        total_emitters=total_emitters,
        required_flow_l_h=required_flow_l_h,
        required_flow_m3_h=required_flow_m3_h,
    )

def get_table_flow_with_reserve(flow_m3_h: float) -> float:
    available_flows = sorted(HEAD_LOSS_TABLE_BAR_PER_100M.keys())

    for table_flow in available_flows:
        if table_flow >= flow_m3_h:
            return table_flow

    max_table_flow = available_flows[-1]

    raise ValueError(
        f"Витрата {flow_m3_h:.2f} м³/год більша, ніж максимальна витрата в таблиці "
        f"{max_table_flow:.2f} м³/год. "
        f"Оберіть більший діаметр труби або поділіть систему поливу на декілька зон."
    )


def calculate_pump_requirement(
    flow_m3_h: float,
    pipe_diameter_mm: int,
    pipe_length_m: float,
    height_difference_m: float,
    drip_tape_pressure_bar: float = 1.0,
    filter_and_fittings_loss_bar: float = 0.4,
    reserve_percent: float = 15,
) -> PumpRequirement:
    if flow_m3_h <= 0:
        raise ValueError("Витрата системи має бути більшою за 0")
    if pipe_length_m < 0:
        raise ValueError("Довжина магістралі не може бути від’ємною")
    if pipe_diameter_mm not in (20, 25, 32, 40, 50, 63, 75):
        raise ValueError("Непідтримуваний діаметр труби")

    nearest_table_flow_m3_h = get_table_flow_with_reserve(flow_m3_h)
    pipe_loss_bar_per_100m = HEAD_LOSS_TABLE_BAR_PER_100M[
        nearest_table_flow_m3_h
    ].get(pipe_diameter_mm)

    if pipe_loss_bar_per_100m is None:
        raise ValueError(
            "Для такої витрати цей діаметр труби не рекомендується. "
            "Оберіть більший діаметр магістралі."
        )

    total_pipe_loss_bar = pipe_loss_bar_per_100m * pipe_length_m / 100
    height_loss_bar = height_difference_m / 10

    required_pressure_bar = (
        drip_tape_pressure_bar
        + total_pipe_loss_bar
        + height_loss_bar
        + filter_and_fittings_loss_bar
    )

    required_pressure_with_reserve_bar = required_pressure_bar * (1 + reserve_percent / 100)
    required_head_m = required_pressure_with_reserve_bar * 10

    return PumpRequirement(
        nearest_table_flow_m3_h=nearest_table_flow_m3_h,
        pipe_loss_bar_per_100m=pipe_loss_bar_per_100m,
        total_pipe_loss_bar=total_pipe_loss_bar,
        height_loss_bar=height_loss_bar,
        drip_tape_pressure_bar=drip_tape_pressure_bar,
        filter_and_fittings_loss_bar=filter_and_fittings_loss_bar,
        required_pressure_bar=required_pressure_bar,
        required_pressure_with_reserve_bar=required_pressure_with_reserve_bar,
        required_head_m=required_head_m,
    )