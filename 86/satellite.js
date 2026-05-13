const EARTH_RADIUS = 6378.137;
const MU = 398600.4418;
const RAD2DEG = 180 / Math.PI;
const DEG2RAD = Math.PI / 180;

class Satellite {
    constructor(name, tle1, tle2) {
        this.name = name;
        this.tle1 = tle1;
        this.tle2 = tle2;
        this.ephemeris = this.parseTLE(tle1, tle2);
        this.entity = null;
        this.color = Cesium.Color.WHITE;
    }
    
    parseTLE(tle1, tle2) {
        const elements = {
            e: parseFloat(tle2.substring(26, 33)) / 10000000,
            inclination: parseFloat(tle2.substring(8, 16)) * DEG2RAD,
            raan: parseFloat(tle2.substring(17, 25)) * DEG2RAD,
            argPe: parseFloat(tle2.substring(34, 42)) * DEG2RAD,
            meanAnomaly: parseFloat(tle2.substring(43, 51)) * DEG2RAD,
            meanMotion: parseFloat(tle2.substring(52, 63)),
            epochYear: parseInt(tle1.substring(18, 20)),
            epochDay: parseFloat(tle1.substring(20, 32)),
            bstar: 0
        };
        
        if (elements.epochYear < 57) {
            elements.epochYear += 2000;
        } else {
            elements.epochYear += 1900;
        }
        
        elements.a = Math.pow(MU / (elements.meanMotion * 2 * Math.PI / 86400), 2/3);
        elements.period = 86400 / elements.meanMotion;
        elements.epoch = this.epochToDate(elements.epochYear, elements.epochDay);
        
        const bstarStr = tle1.substring(53, 59);
        if (bstarStr.trim() !== '') {
            try {
                const mantissa = parseInt(bstarStr.substring(0, 4)) / 10000;
                const exponent = parseInt(bstarStr.substring(4, 5));
                const sign = tle1.charAt(52) === '-' ? -1 : 1;
                elements.bstar = sign * mantissa * Math.pow(10, exponent - 5);
            } catch (e) {
                elements.bstar = 0;
            }
        }
        
        return elements;
    }
    
    epochToDate(year, dayOfYear) {
        const date = new Date(Date.UTC(year, 0, 1));
        const dayFraction = dayOfYear - Math.floor(dayOfYear);
        const daysToAdd = Math.floor(dayOfYear) - 1;
        const hours = dayFraction * 24;
        const hourFraction = hours - Math.floor(hours);
        const minutes = hourFraction * 60;
        const minuteFraction = minutes - Math.floor(minutes);
        const seconds = minuteFraction * 60;
        
        date.setUTCDate(date.getUTCDate() + daysToAdd);
        date.setUTCHours(
            Math.floor(hours),
            Math.floor(minutes),
            Math.floor(seconds),
            Math.floor((seconds - Math.floor(seconds)) * 1000)
        );
        
        return date;
    }
    
    getMinutesSinceEpoch(date) {
        return (date.getTime() - this.ephemeris.epoch.getTime()) / 60000;
    }
    
    solveKepler(M, e, tolerance = 1e-8) {
        let E = M + e * Math.sin(M);
        let dE = 1;
        
        while (Math.abs(dE) > tolerance) {
            dE = (E - e * Math.sin(E) - M) / (1 - e * Math.cos(E));
            E = E - dE;
        }
        
        return E;
    }
    
    getPosition(date) {
        const e = this.ephemeris.e;
        const i = this.ephemeris.inclination;
        const omega = this.ephemeris.raan;
        const w = this.ephemeris.argPe;
        const a = this.ephemeris.a;
        const n = this.ephemeris.meanMotion * 2 * Math.PI / 86400;
        const M0 = this.ephemeris.meanAnomaly;
        
        const dt = this.getMinutesSinceEpoch(date) * 60;
        const M = M0 + n * dt;
        const E = this.solveKepler(M, e);
        
        const cosE = Math.cos(E);
        const sinE = Math.sin(E);
        const nu = Math.atan2(Math.sqrt(1 - e*e) * sinE, cosE - e);
        
        const r = a * (1 - e * cosE);
        
        const cosnu = Math.cos(nu);
        const sinnu = Math.sin(nu);
        
        const xOrbit = r * cosnu;
        const yOrbit = r * sinnu;
        
        const cosw = Math.cos(w);
        const sinw = Math.sin(w);
        const cosi = Math.cos(i);
        const sini = Math.sin(i);
        const cosOmega = Math.cos(omega);
        const sinOmega = Math.sin(omega);
        
        const xECEF = xOrbit * (cosw * cosOmega - sinw * sinOmega * cosi) -
                      yOrbit * (sinw * cosOmega + cosw * sinOmega * cosi);
        const yECEF = xOrbit * (cosw * sinOmega + sinw * cosOmega * cosi) -
                      yOrbit * (sinw * sinOmega - cosw * cosOmega * cosi);
        const zECEF = xOrbit * sinw * sini + yOrbit * cosw * sini;
        
        const jd = this.julianDate(date);
        const gmst = this.greenwichMeanSiderealTime(jd);
        
        const cosTheta = Math.cos(gmst);
        const sinTheta = Math.sin(gmst);
        
        const xECEF2 = xECEF * cosTheta + yECEF * sinTheta;
        const yECEF2 = -xECEF * sinTheta + yECEF * cosTheta;
        
        return Cesium.Cartesian3.fromElements(
            xECEF2 * 1000,
            yECEF2 * 1000,
            zECEF * 1000
        );
    }
    
    getVelocity(date) {
        const e = this.ephemeris.e;
        const i = this.ephemeris.inclination;
        const omega = this.ephemeris.raan;
        const w = this.ephemeris.argPe;
        const a = this.ephemeris.a;
        const n = this.ephemeris.meanMotion * 2 * Math.PI / 86400;
        const M0 = this.ephemeris.meanAnomaly;
        
        const dt = this.getMinutesSinceEpoch(date) * 60;
        const M = M0 + n * dt;
        const E = this.solveKepler(M, e);
        
        const cosE = Math.cos(E);
        const sinE = Math.sin(E);
        const nu = Math.atan2(Math.sqrt(1 - e*e) * sinE, cosE - e);
        
        const r = a * (1 - e * cosE);
        
        const cosnu = Math.cos(nu);
        const sinnu = Math.sin(nu);
        
        const vDot = n * a * a / (r * Math.sqrt(1 - e*e));
        
        const xOrbit = r * cosnu;
        const yOrbit = r * sinnu;
        const vxOrbit = -vDot * sinnu;
        const vyOrbit = vDot * (e + cosnu);
        
        const cosw = Math.cos(w);
        const sinw = Math.sin(w);
        const cosi = Math.cos(i);
        const sini = Math.sin(i);
        const cosOmega = Math.cos(omega);
        const sinOmega = Math.sin(omega);
        
        const xECEF = xOrbit * (cosw * cosOmega - sinw * sinOmega * cosi) -
                      yOrbit * (sinw * cosOmega + cosw * sinOmega * cosi);
        const yECEF = xOrbit * (cosw * sinOmega + sinw * cosOmega * cosi) -
                      yOrbit * (sinw * sinOmega - cosw * cosOmega * cosi);
        const zECEF = xOrbit * sinw * sini + yOrbit * cosw * sini;
        
        const vxECEF = vxOrbit * (cosw * cosOmega - sinw * sinOmega * cosi) -
                       vyOrbit * (sinw * cosOmega + cosw * sinOmega * cosi);
        const vyECEF = vxOrbit * (cosw * sinOmega + sinw * cosOmega * cosi) -
                       vyOrbit * (sinw * sinOmega - cosw * cosOmega * cosi);
        const vzECEF = vxOrbit * sinw * sini + vyOrbit * cosw * sini;
        
        const jd = this.julianDate(date);
        const gmst = this.greenwichMeanSiderealTime(jd);
        
        const cosTheta = Math.cos(gmst);
        const sinTheta = Math.sin(gmst);
        
        const xECEF2 = xECEF * cosTheta + yECEF * sinTheta;
        const yECEF2 = -xECEF * sinTheta + yECEF * cosTheta;
        const vxECEF2 = vxECEF * cosTheta + vyECEF * sinTheta;
        const vyECEF2 = -vxECEF * sinTheta + vyECEF * cosTheta;
        
        return Cesium.Cartesian3.fromElements(
            vxECEF2 * 1000,
            vyECEF2 * 1000,
            vzECEF * 1000
        );
    }
    
    julianDate(date) {
        const year = date.getUTCFullYear();
        const month = date.getUTCMonth() + 1;
        const day = date.getUTCDate();
        const hour = date.getUTCHours();
        const minute = date.getUTCMinutes();
        const second = date.getUTCSeconds();
        
        let a = Math.floor((14 - month) / 12);
        let y = year + 4800 - a;
        let m = month + 12 * a - 3;
        
        let JDN = day + Math.floor((153 * m + 2) / 5) + 365 * y + Math.floor(y / 4) - Math.floor(y / 100) + Math.floor(y / 400) - 32045;
        let JD = JDN + (hour - 12) / 24 + minute / 1440 + second / 86400;
        
        return JD;
    }
    
    greenwichMeanSiderealTime(jd) {
        const T = (jd - 2451545.0) / 36525.0;
        
        let GMST = 280.46061837 + 360.98564736629 * (jd - 2451545.0) +
                   0.000387933 * T * T - T * T * T / 38710000.0;
        
        GMST = ((GMST % 360) + 360) % 360;
        
        return GMST * DEG2RAD;
    }
    
    getOrbitPoints(numPoints = 100) {
        const points = [];
        const period = this.ephemeris.period;
        const now = new Date();
        
        for (let i = 0; i <= numPoints; i++) {
            const time = new Date(now.getTime() + (i / numPoints) * period * 1000);
            points.push(this.getPosition(time));
        }
        
        return points;
    }
    
    getOrbitalElements() {
        return {
            name: this.name,
            semiMajorAxis: this.ephemeris.a,
            eccentricity: this.ephemeris.e,
            inclination: this.ephemeris.inclination * RAD2DEG,
            raan: this.ephemeris.raan * RAD2DEG,
            argumentOfPerigee: this.ephemeris.argPe * RAD2DEG,
            meanAnomaly: this.ephemeris.meanAnomaly * RAD2DEG,
            period: this.ephemeris.period,
            epoch: this.ephemeris.epoch
        };
    }
}

class SatelliteManager {
    constructor() {
        this.satellites = [];
    }
    
    addSatellite(name, tle1, tle2) {
        const satellite = new Satellite(name, tle1, tle2);
        this.satellites.push(satellite);
        return satellite;
    }
    
    removeSatellite(name) {
        const index = this.satellites.findIndex(s => s.name === name);
        if (index !== -1) {
            return this.satellites.splice(index, 1)[0];
        }
        return null;
    }
    
    getSatellite(name) {
        return this.satellites.find(s => s.name === name);
    }
    
    getAllSatellites() {
        return this.satellites;
    }
    
    clearAll() {
        this.satellites = [];
    }
}
