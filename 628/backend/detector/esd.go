package detector

import (
	"math"
	"sort"
)

func mean(data []float64) float64 {
	if len(data) == 0 {
		return 0
	}
	sum := 0.0
	for _, v := range data {
		sum += v
	}
	return sum / float64(len(data))
}

func median(data []float64) float64 {
	if len(data) == 0 {
		return 0
	}
	sorted := make([]float64, len(data))
	copy(sorted, data)
	sort.Float64s(sorted)
	n := len(sorted)
	if n%2 == 0 {
		return (sorted[n/2-1] + sorted[n/2]) / 2
	}
	return sorted[n/2]
}

func mad(data []float64) float64 {
	m := median(data)
	deviations := make([]float64, len(data))
	for i, v := range data {
		deviations[i] = math.Abs(v - m)
	}
	return median(deviations)
}

func studentTCDF(t float64, df int) float64 {
	x := df / (df + t*t)
	return regularizedBeta(x, df/2.0, 0.5)
}

func regularizedBeta(x, a, b float64) float64 {
	if x <= 0 {
		return 0
	}
	if x >= 1 {
		return 1
	}

	bt := math.Exp(lgamma(a)+lgamma(b)-lgamma(a+b)) *
		math.Pow(x, a) * math.Pow(1-x, b)

	if x < (a+1)/(a+b+2) {
		return bt * betaCF(x, a, b) / a
	}
	return 1 - bt*betaCF(1-x, b, a)/b
}

func betaCF(x, a, b float64) float64 {
	maxIter := 200
	eps := 3.0e-7

	qab := a + b
	qap := a + 1
	qam := a - 1

	c := 1.0
	d := 1 - qab*x/qap
	if math.Abs(d) < 1e-30 {
		d = 1e-30
	}
	d = 1 / d
	h := d

	for m := 1; m <= maxIter; m++ {
		mf := float64(m)

		even := mf * (b-mf) * x / ((qam + 2*mf) * (a + 2*mf))
		d = 1 + even*d
		if math.Abs(d) < 1e-30 {
			d = 1e-30
		}
		c = 1 + even/c
		if math.Abs(c) < 1e-30 {
			c = 1e-30
		}
		d = 1 / d
		h *= d * c

		even = -(a + mf) * (qab + mf) * x / ((a + 2*mf) * (qap + 2*mf))
		d = 1 + even*d
		if math.Abs(d) < 1e-30 {
			d = 1e-30
		}
		c = 1 + even/c
		if math.Abs(c) < 1e-30 {
			c = 1e-30
		}
		d = 1 / d
		del := d * c
		h *= del

		if math.Abs(del-1) < eps {
			break
		}
	}

	return h
}

func lgamma(x float64) float64 {
	coefficients := []float64{
		76.18009172947146,
		-86.50532032941677,
		24.01409824083091,
		-1.231739572450155,
		0.1208650973866179e-2,
		-0.5395239384953e-5,
	}

	y := x
	tmp := x + 5.5
	tmp -= (x + 0.5) * math.Log(tmp)
	ser := 1.000000000190015
	for _, c := range coefficients {
		y++
		ser += c / y
	}
	return -tmp + math.Log(2.5066282746310005*ser/x)
}

type ESDResult struct {
	Index      int
	Value      float64
	Expected   float64
	Deviation  float64
	Score      float64
	PValue     float64
}

func GrubbsESD(data []float64, maxAnomalies float64, alpha float64) []ESDResult {
	if len(data) < 3 {
		return nil
	}

	n := len(data)
	maxK := int(maxAnomalies)
	if maxK == 0 {
		maxK = int(math.Ceil(float64(n) * maxAnomalies))
	}
	if maxK > n/2 {
		maxK = n / 2
	}
	if maxK < 1 {
		maxK = 1
	}

	indices := make([]int, n)
	for i := range indices {
		indices[i] = i
	}

	var results []ESDResult
	remaining := make([]float64, n)
	copy(remaining, data)
	remainingIndices := make([]int, n)
	copy(remainingIndices, indices)

	medianVal := median(data)
	madVal := mad(data)
	if madVal == 0 {
		madVal = 1
	}
	modifiedData := make([]float64, n)
	for i, v := range data {
		modifiedData[i] = 0.6745 * (v - medianVal) / madVal
	}

	for k := 0; k < maxK; k++ {
		if len(remaining) < 3 {
			break
		}

		m := mean(remaining)
		maxDev := 0.0
		maxIdx := 0

		for i, v := range remaining {
			dev := math.Abs(v - m)
			if dev > maxDev {
				maxDev = dev
				maxIdx = i
			}
		}

		variance := 0.0
		for _, v := range remaining {
			variance += (v - m) * (v - m)
		}
		sd := math.Sqrt(variance / float64(len(remaining)-1))
		if sd == 0 {
			break
		}

		g := maxDev / sd
		df := len(remaining) - 2
		if df < 1 {
			break
		}

		tSquared := g * g * float64(df) / float64(len(remaining)-2+g*g)
		t := math.Sqrt(tSquared)

		pValue := 2 * (1 - studentTCDF(t, df))
		criticalAlpha := alpha / float64(maxK-k)

		originalIdx := remainingIndices[maxIdx]

		anomaly := ESDResult{
			Index:     originalIdx,
			Value:     data[originalIdx],
			Expected:  m,
			Deviation: maxDev,
			Score:     g,
			PValue:    pValue,
		}

		if pValue < criticalAlpha {
			results = append(results, anomaly)
		} else {
			break
		}

		remaining = append(remaining[:maxIdx], remaining[maxIdx+1:]...)
		remainingIndices = append(remainingIndices[:maxIdx], remainingIndices[maxIdx+1:]...)
	}

	return results
}
