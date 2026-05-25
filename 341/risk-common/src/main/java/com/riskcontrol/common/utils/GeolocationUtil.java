package com.riskcontrol.common.utils;

public class GeolocationUtil {

    private static final double EARTH_RADIUS_KM = 6371.0;

    public static double calculateDistanceKm(double lat1, double lon1, double lat2, double lon2) {
        double dLat = Math.toRadians(lat2 - lat1);
        double dLon = Math.toRadians(lon2 - lon1);

        double a = Math.sin(dLat / 2) * Math.sin(dLat / 2)
                + Math.cos(Math.toRadians(lat1)) * Math.cos(Math.toRadians(lat2))
                * Math.sin(dLon / 2) * Math.sin(dLon / 2);

        double c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

        return EARTH_RADIUS_KM * c;
    }

    public static double calculateVelocityKmPerHour(double lat1, double lon1, long time1,
                                                    double lat2, double lon2, long time2) {
        if (time1 >= time2) {
            return 0.0;
        }

        double distanceKm = calculateDistanceKm(lat1, lon1, lat2, lon2);
        double timeHours = (time2 - time1) / (1000.0 * 60.0 * 60.0);

        if (timeHours <= 0) {
            return Double.MAX_VALUE;
        }

        return distanceKm / timeHours;
    }

    public static boolean isImpossibleTravel(double velocityKmPerHour) {
        return velocityKmPerHour > 1000.0;
    }
}
