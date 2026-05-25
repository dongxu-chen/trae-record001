package com.coupon.rl.buffer;

import com.coupon.rl.model.Experience;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.*;
import java.util.concurrent.ThreadLocalRandom;

@Slf4j
@Component
public class ReplayBuffer {

    private final int maxSize;
    private final Deque<Experience> buffer;
    private final Object lock = new Object();

    public ReplayBuffer() {
        this(100000);
    }

    public ReplayBuffer(int maxSize) {
        this.maxSize = maxSize;
        this.buffer = new LinkedList<>();
    }

    public void add(Experience experience) {
        synchronized (lock) {
            if (buffer.size() >= maxSize) {
                buffer.pollFirst();
            }
            buffer.addLast(experience);
        }
    }

    public List<Experience> sample(int batchSize) {
        synchronized (lock) {
            if (buffer.size() < batchSize) {
                return new ArrayList<>(buffer);
            }

            List<Experience> allExperiences = new ArrayList<>(buffer);
            List<Experience> batch = new ArrayList<>();
            ThreadLocalRandom random = ThreadLocalRandom.current();

            for (int i = 0; i < batchSize; i++) {
                int index = random.nextInt(allExperiences.size());
                batch.add(allExperiences.get(index));
            }

            return batch;
        }
    }

    public List<Experience> samplePriority(int batchSize) {
        synchronized (lock) {
            if (buffer.size() < batchSize) {
                return new ArrayList<>(buffer);
            }

            List<Experience> allExperiences = new ArrayList<>(buffer);
            double[] priorities = new double[allExperiences.size()];
            double totalPriority = 0;

            for (int i = 0; i < allExperiences.size(); i++) {
                Experience exp = allExperiences.get(i);
                double priority = Math.abs(exp.getReward()) + 0.01;
                priorities[i] = priority;
                totalPriority += priority;
            }

            List<Experience> batch = new ArrayList<>();
            ThreadLocalRandom random = ThreadLocalRandom.current();

            for (int i = 0; i < batchSize; i++) {
                double r = random.nextDouble(totalPriority);
                double cumulative = 0;
                for (int j = 0; j < priorities.length; j++) {
                    cumulative += priorities[j];
                    if (r <= cumulative) {
                        batch.add(allExperiences.get(j));
                        break;
                    }
                }
            }

            return batch;
        }
    }

    public int size() {
        synchronized (lock) {
            return buffer.size();
        }
    }

    public boolean isReady(int minSize) {
        return size() >= minSize;
    }

    public void clear() {
        synchronized (lock) {
            buffer.clear();
        }
        log.info("Replay buffer cleared");
    }
}
