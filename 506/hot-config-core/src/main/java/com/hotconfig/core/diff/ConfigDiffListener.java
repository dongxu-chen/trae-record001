package com.hotconfig.core.diff;

@FunctionalInterface
public interface ConfigDiffListener {

    void onConfigDiff(ConfigDiff diff);
}
