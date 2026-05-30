import numpy as np
from typing import List, Dict, Tuple
from .utils import RestaurantConfig, SimulationResult, format_time, calculate_turnover_rate, calculate_satisfaction
from .strategies import QueueStrategy, CustomerGroup, FIFOStrategy, SmartRetentionStrategy
from .table_assignment import TableAssignmentStrategy, create_tables, update_table_status, get_available_tables, get_table_by_id
from .data_generator import RestaurantDataGenerator


class RestaurantSimulation:
    def __init__(
        self,
        config: RestaurantConfig,
        queue_strategy: QueueStrategy = None,
        assignment_strategy: TableAssignmentStrategy = None,
        seed: int = 42,
    ):
        self.config = config
        self.queue_strategy = queue_strategy or FIFOStrategy()
        self.assignment_strategy = assignment_strategy
        np.random.seed(seed)
        self.data_generator = RestaurantDataGenerator(config)

    def run(self, num_runs: int = 1) -> SimulationResult:
        all_results = []

        for run in range(num_runs):
            result = self._run_single_simulation()
            all_results.append(result)

        if num_runs == 1:
            return all_results[0]

        return self._aggregate_results(all_results)

    def _run_single_simulation(self) -> SimulationResult:
        tables = create_tables(self.config)
        arrivals = self.data_generator.generate_daily_arrivals()
        reservations = self.data_generator.generate_reservations()

        queue: List[CustomerGroup] = []
        served_groups: List[CustomerGroup] = []
        lost_groups = 0

        num_hours = self.config.close_hour - self.config.open_hour
        hourly_arrivals = [0] * num_hours
        hourly_served = [0] * num_hours
        hourly_satisfaction_sum = [0.0] * num_hours
        hourly_satisfaction_count = [0] * num_hours
        hourly_reservations = [0] * num_hours
        hourly_no_shows = [0] * num_hours
        queue_length_history = []
        table_occupancy_timeline = {t.id: [] for t in tables}
        state_change_events = []

        total_reservations = 0
        reservation_no_shows = 0
        reservation_late_arrivals = 0
        no_show_wasted_minutes = 0.0

        retention_offers_sent = 0
        retention_offers_accepted = 0
        retention_revenue_saved = 0.0
        retention_discount_cost = 0.0

        dish_time_tracker: Dict[str, List[float]] = {}
        for d in self.config.dishes:
            dish_time_tracker[d.name] = []

        reserved_slots: Dict[int, Tuple[float, int]] = {}

        for res in reservations:
            total_reservations += 1
            res_hour = int(res["reserved_time"] // 60) - self.config.open_hour
            if 0 <= res_hour < num_hours:
                hourly_reservations[res_hour] += 1

            if res["is_no_show"]:
                reservation_no_shows += 1
                if 0 <= res_hour < num_hours:
                    hourly_no_shows[res_hour] += 1
                no_show_wasted_minutes += 30.0

                state_change_events.append({
                    "time": res["reserved_time"],
                    "type": "no_show",
                    "group_size": res["group_size"],
                    "reserved_time": res["reserved_time"],
                })
            elif res["is_late"]:
                reservation_late_arrivals += 1
                late_extra = res["actual_arrival"] - res["reserved_time"]
                no_show_wasted_minutes += max(0, late_extra - self.config.reservation_config.late_tolerance_minutes)

        event_list = []
        for idx, item in enumerate(arrivals):
            arr_time, group_size, dining_time, dish_name, dish_price, is_res = item
            event_list.append(("arrival", arr_time, idx, group_size, dining_time, dish_name, dish_price, is_res))

        for res in reservations:
            if not res["is_no_show"] and res["actual_arrival"] is not None:
                event_list.append((
                    "reservation_arrival",
                    res["actual_arrival"],
                    10000 + res["id"],
                    res["group_size"],
                    0,
                    res["dish_name"],
                    res["dish_price"],
                    True,
                ))

        event_list.sort(key=lambda x: x[1])

        current_time = self.config.open_hour * 60
        event_idx = 0

        while current_time < self.config.close_hour * 60:
            while event_idx < len(event_list) and event_list[event_idx][1] <= current_time:
                event = event_list[event_idx]
                evt_type = event[0]
                _, arr_time, group_id, group_size, dining_time, dish_name, dish_price, is_res = event

                hour_idx = int(arr_time // 60) - self.config.open_hour
                if 0 <= hour_idx < num_hours:
                    hourly_arrivals[hour_idx] += 1

                if evt_type == "reservation_arrival" and dining_time == 0:
                    base_dining = np.random.lognormal(self.config.lognormal_mu, self.config.lognormal_sigma)
                    from .utils import adjust_dining_time_by_dish
                    dining_time = adjust_dining_time_by_dish(
                        max(15, min(180, base_dining)), dish_name, self.config
                    )

                group = CustomerGroup(
                    id=group_id,
                    arrival_time=arr_time,
                    size=group_size,
                    dining_time=dining_time,
                    is_reservation=is_res,
                    dish_name=dish_name,
                    dish_price=dish_price,
                )
                queue.append(group)

                state_change_events.append({
                    "time": arr_time,
                    "type": "arrival",
                    "group_id": group_id,
                    "group_size": group_size,
                    "queue_length": len(queue),
                    "is_reservation": is_res,
                    "dish_name": dish_name,
                })

                event_idx += 1

            update_table_status(tables, current_time)

            for table in tables:
                if table.is_occupied and table.occupied_until <= current_time:
                    table.is_occupied = False
                    state_change_events.append({
                        "time": current_time,
                        "type": "vacate",
                        "table_id": table.id,
                        "table_capacity": table.capacity,
                    })

            if isinstance(self.queue_strategy, SmartRetentionStrategy):
                ret_config = self.config.retention_config
                current_hour_idx = int(current_time // 60) - self.config.open_hour
                discounts_this_hour = 0

                for group in queue:
                    wait = current_time - group.arrival_time
                    if wait >= ret_config.wait_threshold and not group.retention_offered:
                        if discounts_this_hour < ret_config.max_discounts_per_hour:
                            group.retention_offered = True
                            retention_offers_sent += 1
                            discounts_this_hour += 1

                            if np.random.random() < ret_config.retention_success_rate:
                                group.retention_accepted = True
                                retention_offers_accepted += 1
                                retention_revenue_saved += group.size * self.config.avg_spend_per_person
                                retention_discount_cost += (
                                    group.size * self.config.avg_spend_per_person * ret_config.discount_rate
                                )

            available_tables = get_available_tables(tables)

            while queue and available_tables:
                selected_group, table_id = self.queue_strategy.select_next_group(
                    queue, available_tables
                )

                if selected_group is None:
                    break

                table = get_table_by_id(tables, table_id)
                if table and not table.is_occupied:
                    wait_time = current_time - selected_group.arrival_time
                    selected_group.wait_time = wait_time
                    selected_group.table_id = table_id

                    table.is_occupied = True
                    table.occupied_until = current_time + selected_group.dining_time
                    table.total_occupied_time += selected_group.dining_time

                    table_occupancy_timeline[table_id].append(
                        (current_time, table.occupied_until, selected_group.size)
                    )

                    satisfaction = calculate_satisfaction(wait_time, self.config)
                    hour_idx = int(current_time // 60) - self.config.open_hour
                    if 0 <= hour_idx < num_hours:
                        hourly_served[hour_idx] += 1
                        hourly_satisfaction_sum[hour_idx] += satisfaction
                        hourly_satisfaction_count[hour_idx] += 1

                    if selected_group.dish_name in dish_time_tracker:
                        dish_time_tracker[selected_group.dish_name].append(
                            selected_group.dining_time
                        )

                    state_change_events.append({
                        "time": current_time,
                        "type": "seat",
                        "table_id": table_id,
                        "table_capacity": table.capacity,
                        "group_id": selected_group.id,
                        "group_size": selected_group.size,
                        "wait_time": wait_time,
                        "satisfaction": satisfaction,
                        "expected_end": table.occupied_until,
                        "is_reservation": selected_group.is_reservation,
                        "dish_name": selected_group.dish_name,
                        "retention_accepted": selected_group.retention_accepted,
                    })

                    served_groups.append(selected_group)
                    queue.remove(selected_group)

                    available_tables = get_available_tables(tables)
                else:
                    break

            queue_length_history.append((current_time, len(queue)))

            next_event_time = self.config.close_hour * 60 + 1
            if event_idx < len(event_list):
                next_event_time = min(next_event_time, event_list[event_idx][1])

            for table in tables:
                if table.is_occupied and table.occupied_until > current_time:
                    next_event_time = min(next_event_time, table.occupied_until)

            if next_event_time > current_time:
                current_time = next_event_time
            else:
                current_time += 1

        lost_groups = len(queue)

        return self._compile_results(
            served_groups=served_groups,
            lost_groups=lost_groups,
            tables=tables,
            hourly_arrivals=hourly_arrivals,
            hourly_served=hourly_served,
            queue_length_history=queue_length_history,
            table_occupancy_timeline=table_occupancy_timeline,
            state_change_events=state_change_events,
            hourly_satisfaction_sum=hourly_satisfaction_sum,
            hourly_satisfaction_count=hourly_satisfaction_count,
            total_reservations=total_reservations,
            reservation_no_shows=reservation_no_shows,
            reservation_late_arrivals=reservation_late_arrivals,
            no_show_wasted_minutes=no_show_wasted_minutes,
            hourly_reservations=hourly_reservations,
            hourly_no_shows=hourly_no_shows,
            retention_offers_sent=retention_offers_sent,
            retention_offers_accepted=retention_offers_accepted,
            retention_revenue_saved=retention_revenue_saved,
            retention_discount_cost=retention_discount_cost,
            dish_time_tracker=dish_time_tracker,
        )

    def _compile_results(
        self,
        served_groups: List[CustomerGroup],
        lost_groups: int,
        tables,
        hourly_arrivals: List[int],
        hourly_served: List[int],
        queue_length_history: List[Tuple[float, int]],
        table_occupancy_timeline: Dict[int, List[Tuple[float, float, int]]],
        state_change_events: List[Dict],
        hourly_satisfaction_sum: List[float],
        hourly_satisfaction_count: List[int],
        total_reservations: int,
        reservation_no_shows: int,
        reservation_late_arrivals: int,
        no_show_wasted_minutes: float,
        hourly_reservations: List[int],
        hourly_no_shows: List[int],
        retention_offers_sent: int,
        retention_offers_accepted: int,
        retention_revenue_saved: float,
        retention_discount_cost: float,
        dish_time_tracker: Dict[str, List[float]],
    ) -> SimulationResult:
        result = SimulationResult()
        result.strategy_name = self.queue_strategy.get_name()

        total_arrivals = sum(hourly_arrivals)
        result.total_arrivals = total_arrivals
        result.total_served = len(served_groups)
        result.total_lost = lost_groups

        satisfaction_scores = []
        if served_groups:
            wait_times = [g.wait_time for g in served_groups]
            result.average_wait_time = np.mean(wait_times)
            result.median_wait_time = np.median(wait_times)
            result.wait_times = wait_times

            dining_times = [g.dining_time for g in served_groups]
            result.average_dining_time = np.mean(dining_times)

            total_revenue = 0.0
            for g in served_groups:
                spend = g.size * self.config.avg_spend_per_person
                if g.retention_accepted:
                    spend *= (1 - self.config.retention_config.discount_rate)
                total_revenue += spend
            result.revenue = total_revenue

            for g in served_groups:
                sat = calculate_satisfaction(g.wait_time, self.config)
                satisfaction_scores.append(sat)

            result.satisfaction_scores = satisfaction_scores
            result.satisfaction_score = np.mean(satisfaction_scores) if satisfaction_scores else 0.0

            penalty_per_group = self.config.satisfaction_decay_rate * max(0, result.average_wait_time - self.config.satisfaction_threshold)
            result.wait_time_penalty = penalty_per_group * len(served_groups)

            result.net_benefit = result.revenue - result.wait_time_penalty * 10

        hourly_satisfaction = []
        for i in range(len(hourly_served)):
            if hourly_satisfaction_count[i] > 0:
                hourly_satisfaction.append(hourly_satisfaction_sum[i] / hourly_satisfaction_count[i])
            else:
                hourly_satisfaction.append(1.0)
        result.hourly_satisfaction = hourly_satisfaction

        operating_hours = self.config.close_hour - self.config.open_hour
        total_tables = len(tables)
        result.table_turnover_rate = calculate_turnover_rate(
            len(served_groups), total_tables, operating_hours
        )

        table_utilization = {}
        total_available_time = operating_hours * 60

        for table in tables:
            utilization = (table.total_occupied_time / total_available_time) * 100
            table_utilization[table.id] = [table.capacity, utilization]

        result.table_utilization = table_utilization
        result.overall_utilization = np.mean(
            [u[1] for u in table_utilization.values()]
        )

        result.hourly_arrivals = hourly_arrivals
        result.hourly_served = hourly_served
        result.queue_length_history = queue_length_history
        result.table_occupancy_timeline = table_occupancy_timeline
        result.state_change_events = state_change_events

        result.total_reservations = total_reservations
        result.reservation_no_shows = reservation_no_shows
        result.reservation_late_arrivals = reservation_late_arrivals
        result.reservation_show_rate = (
            (total_reservations - reservation_no_shows) / total_reservations
            if total_reservations > 0
            else 1.0
        )
        result.no_show_wasted_minutes = no_show_wasted_minutes
        result.hourly_reservations = hourly_reservations
        result.hourly_no_shows = hourly_no_shows

        if total_reservations > 0 and operating_hours > 0:
            potential_turnover = result.table_turnover_rate + (
                reservation_no_shows / (total_tables * operating_hours)
            )
            result.no_show_impact_on_turnover = (
                potential_turnover - result.table_turnover_rate
            )

        result.retention_offers_sent = retention_offers_sent
        result.retention_offers_accepted = retention_offers_accepted
        result.retention_success_rate = (
            retention_offers_accepted / retention_offers_sent
            if retention_offers_sent > 0
            else 0.0
        )
        result.retention_revenue_saved = retention_revenue_saved
        result.retention_discount_cost = retention_discount_cost

        dish_combination_impact = {}
        dish_dining_time_correlation = []
        for dish_name, times in dish_time_tracker.items():
            if times:
                avg_time = np.mean(times)
                std_time = np.std(times) if len(times) > 1 else 0
                count = len(times)
                dish_info = {
                    "avg_dining_time": round(avg_time, 2),
                    "std_dining_time": round(std_time, 2),
                    "count": count,
                    "turnover_impact": round(60.0 / avg_time, 2) if avg_time > 0 else 0,
                }
                dish_combination_impact[dish_name] = dish_info
                dish_dining_time_correlation.append({
                    "dish_name": dish_name,
                    "avg_dining_time": round(avg_time, 2),
                    "count": count,
                })

        result.dish_combination_impact = dish_combination_impact
        result.dish_dining_time_correlation = dish_dining_time_correlation

        return result

    def _aggregate_results(self, results: List[SimulationResult]) -> SimulationResult:
        aggregated = SimulationResult()
        aggregated.strategy_name = results[0].strategy_name

        aggregated.total_arrivals = int(np.mean([r.total_arrivals for r in results]))
        aggregated.total_served = int(np.mean([r.total_served for r in results]))
        aggregated.total_lost = int(np.mean([r.total_lost for r in results]))
        aggregated.average_wait_time = np.mean([r.average_wait_time for r in results])
        aggregated.median_wait_time = np.mean([r.median_wait_time for r in results])
        aggregated.average_dining_time = np.mean([r.average_dining_time for r in results])
        aggregated.table_turnover_rate = np.mean([r.table_turnover_rate for r in results])
        aggregated.overall_utilization = np.mean([r.overall_utilization for r in results])
        aggregated.revenue = np.mean([r.revenue for r in results])
        aggregated.satisfaction_score = np.mean([r.satisfaction_score for r in results])
        aggregated.wait_time_penalty = np.mean([r.wait_time_penalty for r in results])
        aggregated.net_benefit = np.mean([r.net_benefit for r in results])

        aggregated.total_reservations = int(np.mean([r.total_reservations for r in results]))
        aggregated.reservation_no_shows = int(np.mean([r.reservation_no_shows for r in results]))
        aggregated.reservation_show_rate = np.mean([r.reservation_show_rate for r in results])
        aggregated.no_show_wasted_minutes = np.mean([r.no_show_wasted_minutes for r in results])
        aggregated.no_show_impact_on_turnover = np.mean([r.no_show_impact_on_turnover for r in results])

        aggregated.retention_offers_sent = int(np.mean([r.retention_offers_sent for r in results]))
        aggregated.retention_offers_accepted = int(np.mean([r.retention_offers_accepted for r in results]))
        aggregated.retention_success_rate = np.mean([r.retention_success_rate for r in results])
        aggregated.retention_revenue_saved = np.mean([r.retention_revenue_saved for r in results])
        aggregated.retention_discount_cost = np.mean([r.retention_discount_cost for r in results])

        aggregated.hourly_arrivals = [
            int(np.mean([r.hourly_arrivals[i] for r in results]))
            for i in range(len(results[0].hourly_arrivals))
        ]
        aggregated.hourly_served = [
            int(np.mean([r.hourly_served[i] for r in results]))
            for i in range(len(results[0].hourly_served))
        ]
        aggregated.hourly_reservations = [
            int(np.mean([r.hourly_reservations[i] for r in results]))
            for i in range(len(results[0].hourly_reservations))
        ]
        aggregated.hourly_no_shows = [
            int(np.mean([r.hourly_no_shows[i] for r in results]))
            for i in range(len(results[0].hourly_no_shows))
        ]

        if results:
            aggregated.table_utilization = results[0].table_utilization
            aggregated.table_occupancy_timeline = results[0].table_occupancy_timeline
            aggregated.queue_length_history = results[0].queue_length_history
            aggregated.wait_times = results[0].wait_times
            aggregated.satisfaction_scores = results[0].satisfaction_scores
            aggregated.hourly_satisfaction = results[0].hourly_satisfaction
            aggregated.state_change_events = results[0].state_change_events
            aggregated.dish_combination_impact = results[0].dish_combination_impact
            aggregated.dish_dining_time_correlation = results[0].dish_dining_time_correlation

        return aggregated


def compare_strategies(
    config: RestaurantConfig, strategies: Dict[str, QueueStrategy], num_runs: int = 3
) -> Dict[str, SimulationResult]:
    results = {}

    for name, strategy in strategies.items():
        simulation = RestaurantSimulation(config, queue_strategy=strategy)
        results[name] = simulation.run(num_runs=num_runs)

    return results
