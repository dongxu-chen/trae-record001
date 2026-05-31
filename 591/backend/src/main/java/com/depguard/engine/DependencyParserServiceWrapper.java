package com.depguard.engine;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class DependencyParserServiceWrapper {

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class ParsedDependency {
        private String groupId;
        private String artifactId;
        private String version;
        private String scope;
        private boolean isDirect;
        private Boolean isOutdated;
        private String latestVersion;

        public boolean isDirect() {
            return isDirect;
        }

        public void setDirect(boolean direct) {
            isDirect = direct;
        }
    }
}
