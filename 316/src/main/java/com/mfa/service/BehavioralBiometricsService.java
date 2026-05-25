package com.mfa.service;

import com.mfa.dto.BehavioralBiometrics;
import com.mfa.dto.BehavioralDataRequest;
import com.mfa.dto.BehavioralProfile;
import com.mfa.dto.RiskAssessment;
import com.mfa.entity.User;

public interface BehavioralBiometricsService {

    BehavioralBiometrics analyzeBehavior(BehavioralDataRequest request, User user);

    BehavioralProfile getUserProfile(String userId);

    void updateProfile(String userId, BehavioralBiometrics biometrics);

    RiskAssessment assessBehaviorRisk(BehavioralBiometrics biometrics);

    double calculateSimilarity(BehavioralProfile baseline, BehavioralProfile current);

    void calibrateProfile(String userId, BehavioralDataRequest request);

    boolean isProfileCalibrated(String userId);
}
