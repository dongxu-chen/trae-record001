package com.taskscheduler.core.strategy;

import com.taskscheduler.common.entity.ExecutorInfo;
import com.taskscheduler.common.enums.ExecutorRouteStrategyEnum;

import java.util.List;
import java.util.Random;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;

public interface ExecutorRouteStrategy {

    ExecutorInfo route(List<ExecutorInfo> executors, Long taskId);

    static ExecutorRouteStrategy getStrategy(ExecutorRouteStrategyEnum strategyEnum) {
        return switch (strategyEnum) {
            case RANDOM -> new RandomStrategy();
            case CONSISTENT_HASH -> new ConsistentHashStrategy();
            default -> new RoundRobinStrategy();
        };
    }

    class RoundRobinStrategy implements ExecutorRouteStrategy {

        private final ConcurrentHashMap<Long, AtomicInteger> countMap = new ConcurrentHashMap<>();

        @Override
        public ExecutorInfo route(List<ExecutorInfo> executors, Long taskId) {
            if (executors == null || executors.isEmpty()) {
                return null;
            }
            AtomicInteger count = countMap.computeIfAbsent(taskId, k -> new AtomicInteger(0));
            int index = count.getAndIncrement() % executors.size();
            if (index < 0) {
                count.set(0);
                index = 0;
            }
            return executors.get(index);
        }
    }

    class RandomStrategy implements ExecutorRouteStrategy {

        private final Random random = new Random();

        @Override
        public ExecutorInfo route(List<ExecutorInfo> executors, Long taskId) {
            if (executors == null || executors.isEmpty()) {
                return null;
            }
            int index = random.nextInt(executors.size());
            return executors.get(index);
        }
    }

    class ConsistentHashStrategy implements ExecutorRouteStrategy {

        @Override
        public ExecutorInfo route(List<ExecutorInfo> executors, Long taskId) {
            if (executors == null || executors.isEmpty()) {
                return null;
            }
            int hashCode = taskId.hashCode();
            int index = (hashCode & Integer.MAX_VALUE) % executors.size();
            return executors.get(index);
        }
    }
}
