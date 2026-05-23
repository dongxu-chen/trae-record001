package com.log.collector.util;

import org.junit.Before;
import org.junit.Test;

import static org.junit.Assert.*;

public class BackpressureManagerTest {

    private BackpressureManager manager;

    @Before
    public void setUp() {
        manager = BackpressureManager.getInstance();
        manager.configure(0.85, 0.50, 100, 1000);
        manager.reset();
    }

    @Test
    public void testBackpressureTrigger() {
        assertFalse("初始状态不应有背压", manager.isBackpressureActive());

        manager.shouldTriggerBackpressure(0.9);
        assertTrue("超过高水位应该触发背压", manager.isBackpressureActive());

        manager.shouldReleaseBackpressure(0.4);
        assertFalse("低于低水位应该释放背压", manager.isBackpressureActive());
    }

    @Test
    public void testBackpressureNotTriggeredBelowThreshold() {
        manager.shouldTriggerBackpressure(0.7);
        assertFalse("低于高水位不应触发背压", manager.isBackpressureActive());
    }

    @Test
    public void testBackpressureNotReleasedAboveThreshold() {
        manager.shouldTriggerBackpressure(0.9);
        assertTrue("应该触发背压", manager.isBackpressureActive());

        manager.shouldReleaseBackpressure(0.7);
        assertTrue("高于低水位不应释放背压", manager.isBackpressureActive());
    }

    @Test
    public void testMinBackpressureDuration() throws InterruptedException {
        manager.shouldTriggerBackpressure(0.9);
        assertTrue("应该触发背压", manager.isBackpressureActive());

        Thread.sleep(50);
        manager.shouldReleaseBackpressure(0.4);
        assertTrue("最小持续时间内不应释放背压", manager.isBackpressureActive());

        Thread.sleep(100);
        manager.shouldReleaseBackpressure(0.4);
        assertFalse("超过最小持续时间应该释放背压", manager.isBackpressureActive());
    }

    @Test
    public void testPauseLogic() throws InterruptedException {
        manager.configure(0.85, 0.50, 100, 500);
        manager.shouldTriggerBackpressure(0.9);

        assertTrue("背压激活时应该暂停", manager.shouldPause());
        assertTrue(manager.getRecommendedPauseTime() > 0);

        Thread.sleep(600);
        assertFalse("超过最大持续时间不应暂停", manager.shouldPause());
    }

    @Test
    public void testBackpressureCounts() {
        assertEquals(0, manager.getBackpressureTriggerCount());
        assertEquals(0, manager.getBackpressureReleaseCount());

        manager.shouldTriggerBackpressure(0.9);
        assertEquals(1, manager.getBackpressureTriggerCount());

        try {
            Thread.sleep(150);
        } catch (InterruptedException e) {
        }
        manager.shouldReleaseBackpressure(0.4);
        assertEquals(1, manager.getBackpressureReleaseCount());
    }
}
