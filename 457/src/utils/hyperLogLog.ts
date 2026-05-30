export class HyperLogLog {
  private registers: Uint8Array;
  private precision: number;
  private m: number;
  private alphaMM: number;
  private exactSet: Set<number> | null;
  private exactThreshold: number;

  constructor(precision: number = 14) {
    this.precision = precision;
    this.m = 1 << precision;
    this.alphaMM = this.getAlpha() * this.m * this.m;
    this.exactSet = new Set();
    this.exactThreshold = Math.floor(this.m * 0.1);
    this.registers = new Uint8Array(this.m);
  }

  private getAlpha(): number {
    switch (this.precision) {
      case 4: return 0.673;
      case 5: return 0.697;
      case 6: return 0.709;
      default: return 0.7213 / (1 + 1.079 / this.m);
    }
  }

  private hash(value: string | number): number {
    const str = String(value);
    let h1 = 0xdeadbeef;
    let h2 = 0x41c6ce57;
    
    for (let i = 0; i < str.length; i++) {
      const ch = str.charCodeAt(i);
      h1 = Math.imul(h1 ^ ch, 2654435761);
      h2 = Math.imul(h2 ^ ch, 1597334677);
    }
    
    h1 = Math.imul(h1 ^ (h1 >>> 16), 2246822507);
    h1 ^= Math.imul(h2 ^ (h2 >>> 13), 3266489909);
    h2 = Math.imul(h2 ^ (h2 >>> 16), 2246822507);
    h2 ^= Math.imul(h1 ^ (h1 >>> 13), 3266489909);
    
    const hash = 4294967296 * (2097151 & h2) + (h1 >>> 0);
    return hash >>> 0;
  }

  private getLeadingZeros(x: number): number {
    if (x === 0) return 32;
    let n = 0;
    while ((x & 0x80000000) === 0) {
      n++;
      x <<= 1;
    }
    return n;
  }

  add(value: string | number): void {
    const hashValue = this.hash(value);

    if (this.exactSet !== null) {
      this.exactSet.add(hashValue);
      if (this.exactSet.size > this.exactThreshold) {
        this.convertToHLL();
      }
      return;
    }

    const index = hashValue >>> (32 - this.precision);
    const w = hashValue << this.precision;
    const rho = w === 0 ? 32 - this.precision + 1 : this.getLeadingZeros(w) + 1;
    
    if (rho > this.registers[index]) {
      this.registers[index] = rho;
    }
  }

  private convertToHLL(): void {
    if (this.exactSet === null) return;
    
    for (const hashValue of this.exactSet) {
      const index = hashValue >>> (32 - this.precision);
      const w = hashValue << this.precision;
      const rho = w === 0 ? 32 - this.precision + 1 : this.getLeadingZeros(w) + 1;
      
      if (rho > this.registers[index]) {
        this.registers[index] = rho;
      }
    }
    
    this.exactSet = null;
  }

  count(): number {
    if (this.exactSet !== null) {
      return this.exactSet.size;
    }

    let sum = 0;
    let zeros = 0;
    
    for (let i = 0; i < this.m; i++) {
      const val = this.registers[i];
      sum += 1 / (1 << val);
      if (val === 0) zeros++;
    }

    let estimate = this.alphaMM / sum;

    if (estimate <= 2.5 * this.m && zeros > 0) {
      estimate = this.m * Math.log(this.m / zeros);
    } else if (estimate > (1 / 30) * Math.pow(2, 32)) {
      estimate = -Math.pow(2, 32) * Math.log(1 - estimate / Math.pow(2, 32));
    }

    return Math.round(estimate);
  }

  isUsingExact(): boolean {
    return this.exactSet !== null;
  }

  merge(other: HyperLogLog): HyperLogLog {
    if (this.precision !== other.precision) {
      throw new Error('Cannot merge HLLs with different precision');
    }

    const merged = new HyperLogLog(this.precision);
    merged.convertToHLL();

    for (let i = 0; i < this.m; i++) {
      merged.registers[i] = Math.max(
        this.exactSet !== null ? this.getRegisterFromExact(i) : this.registers[i],
        other.exactSet !== null ? other.getRegisterFromExact(i) : other.registers[i]
      );
    }

    return merged;
  }

  private getRegisterFromExact(index: number): number {
    if (this.exactSet === null) return 0;
    
    let maxRho = 0;
    for (const hashValue of this.exactSet) {
      const idx = hashValue >>> (32 - this.precision);
      if (idx === index) {
        const w = hashValue << this.precision;
        const rho = w === 0 ? 32 - this.precision + 1 : this.getLeadingZeros(w) + 1;
        maxRho = Math.max(maxRho, rho);
      }
    }
    return maxRho;
  }

  clear(): void {
    this.registers.fill(0);
    this.exactSet = new Set();
  }

  getStats(): {
    count: number;
    precision: number;
    isExact: boolean;
    memoryBytes: number;
  } {
    return {
      count: this.count(),
      precision: this.precision,
      isExact: this.isUsingExact(),
      memoryBytes: this.m + (this.exactSet ? this.exactSet.size * 8 : 0),
    };
  }
}

export class HybridDistinctCounter {
  private counters: Map<string, HyperLogLog> = new Map();
  private precision: number;

  constructor(precision: number = 14) {
    this.precision = precision;
  }

  add(key: string, value: string | number): void {
    if (!this.counters.has(key)) {
      this.counters.set(key, new HyperLogLog(this.precision));
    }
    this.counters.get(key)!.add(value);
  }

  count(key: string): number {
    const counter = this.counters.get(key);
    return counter ? counter.count() : 0;
  }

  getCounter(key: string): HyperLogLog | undefined {
    return this.counters.get(key);
  }

  getAllCounts(): Map<string, number> {
    const result = new Map<string, number>();
    for (const [key, counter] of this.counters) {
      result.set(key, counter.count());
    }
    return result;
  }

  clear(): void {
    this.counters.clear();
  }

  merge(other: HybridDistinctCounter): HybridDistinctCounter {
    const merged = new HybridDistinctCounter(this.precision);
    
    const allKeys = new Set([...this.counters.keys(), ...other.counters.keys()]);
    
    for (const key of allKeys) {
      const counter1 = this.counters.get(key);
      const counter2 = other.counters.get(key);
      
      if (counter1 && counter2) {
        merged.counters.set(key, counter1.merge(counter2));
      } else if (counter1) {
        merged.counters.set(key, counter1);
      } else if (counter2) {
        merged.counters.set(key, counter2);
      }
    }
    
    return merged;
  }
}
