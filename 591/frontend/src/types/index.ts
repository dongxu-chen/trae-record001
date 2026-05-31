export interface Repository {
  id: number;
  name: string;
  fullName: string;
  htmlUrl: string;
  defaultBranch: string;
  buildTool: 'MAVEN' | 'GRADLE';
  lastScanTime: string | null;
  scanStatus: 'IDLE' | 'SCANNING' | 'COMPLETED' | 'FAILED';
  healthScore: number;
}

export interface Dependency {
  groupId: string;
  artifactId: string;
  version: string;
  latestVersion: string;
  scope: string;
  isOutdated: boolean;
  isDirect: boolean;
  transitiveDependencies: Dependency[];
}

export interface VersionConflict {
  groupId: string;
  artifactId: string;
  versions: { service: string; version: string }[];
  recommendedVersion: string;
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
}

export interface Vulnerability {
  cveId: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  cvssScore: number;
  description: string;
  affectedVersions: string;
  fixedVersion: string;
  publishedDate: string;
  affectedServices: { repoId: number; repoName: string; dependency: string; version: string }[];
}

export interface UpgradeSuggestion {
  id: number;
  repoId: number;
  repoName: string;
  groupId: string;
  artifactId: string;
  currentVersion: string;
  targetVersion: string;
  upgradeType: 'PATCH' | 'MINOR' | 'MAJOR';
  riskLevel: 'SAFE' | 'LOW_RISK' | 'MEDIUM_RISK' | 'HIGH_RISK';
  compatibilityScore: number;
  breakingChanges: string[];
  releaseNotes: string;
  selected: boolean;
}

export interface BatchPRRequest {
  upgrades: { suggestionId: number }[];
  branchName: string;
  prTitle: string;
  prBody: string;
}

export interface BatchPRResponse {
  pullRequestUrl: string;
  pullRequestNumber: number;
  branchName: string;
  modifiedFiles: string[];
  createdPRs: string[];
  errors: string[];
  totalRequested: number;
  successCount: number;
}

export interface BatchPRVerifyResponse {
  verificationResults: BuildVerificationResult[];
  verifiedCount: number;
  failedCount: number;
  prResult?: BatchPRResponse;
}

export interface BuildVerificationResult {
  buildId: string;
  repoId: number;
  upgradeIds: number[];
  status: 'PENDING' | 'RUNNING' | 'SUCCESS' | 'FAILED' | 'SKIPPED';
  buildSuccess: boolean;
  testsPassed: boolean;
  buildLog: string;
  errorMessage: string;
  startTime: string;
  endTime: string;
  durationMs: number;
}

export interface DashboardStats {
  totalServices: number;
  totalDependencies: number;
  conflictCount: number;
  vulnerabilityCount: number;
  outdatedCount: number;
  healthScore: number;
  recentScans: { repoName: string; time: string; status: string; findings: number }[];
  topVulnerabilities: Vulnerability[];
}

export interface ScanResult {
  id: number;
  repoId: number;
  scanTime: string;
  status: string;
  totalDeps: number;
  conflictCount: number;
  vulnerabilityCount: number;
  outdatedCount: number;
}

export type SeverityLevel = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
export type RiskLevel = 'SAFE' | 'LOW_RISK' | 'MEDIUM_RISK' | 'HIGH_RISK';
export type UpgradeType = 'PATCH' | 'MINOR' | 'MAJOR';

export interface HealthScore {
  dependencyKey: string;
  overallScore: number;
  grade: string;
  vulnerabilityScore: number;
  freshnessScore: number;
  popularityScore: number;
  recommendations: string[];
}

export interface ProjectHealthResponse {
  overallScore: number;
  grade: string;
  healthyCount: number;
  warningCount: number;
  criticalCount: number;
  averageVulnerabilityScore: number;
  averageFreshnessScore: number;
  averagePopularityScore: number;
  dependencies: DependencyWithHealth[];
}

export interface DependencyWithHealth {
  dependency: Dependency;
  healthScore: HealthScore;
}

export interface DependencyUsageResponse {
  groupId: string;
  artifactId: string;
  version: string;
  scope: string;
  isUsed: boolean;
  isDirectlyUsed: boolean;
  usageConfidence: number;
  usageEvidence: string[];
  isSpecialScope: boolean;
}

export interface UsageAnalysisResponse {
  dependencyResults: DependencyUsageResponse[];
  usedCount: number;
  unusedCount: number;
  unclearCount: number;
  unusedDependencies: DependencyUsageResponse[];
  allImportedPackages: string[];
  allUsedClasses: string[];
}

export interface AutoUpgradeConfigResponse {
  minCompatibilityScore: number;
  minHealthScore: number;
  allowedUpgradeTypes: UpgradeType[];
  allowedRiskLevels: RiskLevel[];
}

export interface AutoUpgradeResponse {
  autoUpgradeCandidates: UpgradeSuggestion[];
  manualReviewRequired: UpgradeSuggestion[];
  summary: {
    autoUpgradeCount: number;
    manualReviewCount: number;
    patchUpgrades: number;
    minorUpgrades: number;
    majorUpgrades: number;
    highRiskCount: number;
    averageCompatibilityScore: number;
    minCompatibilityThreshold: number;
    allowedUpgradeTypes: UpgradeType[];
    allowedRiskLevels: RiskLevel[];
  };
}

export interface AutoUpgradeExecutionResponse {
  startTime: string;
  endTime: string;
  totalRequested: number;
  successCount: number;
  failureCount: number;
  skippedCount: number;
  successes: AutoUpgradeResult[];
  failures: AutoUpgradeResult[];
  skipped: AutoUpgradeResult[];
  prUrl?: string;
  prError?: string;
}

export interface AutoUpgradeResult {
  groupId: string;
  artifactId: string;
  currentVersion: string;
  targetVersion: string;
  success: boolean;
  skipped: boolean;
  message: string;
}
