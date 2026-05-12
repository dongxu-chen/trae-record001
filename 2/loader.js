const ATOM_DATA = Object.freeze({
    'H': { color: 0xffffff, radius: 0.31 },
    'C': { color: 0x404040, radius: 0.77 },
    'N': { color: 0x0000ff, radius: 0.75 },
    'O': { color: 0xff0000, radius: 0.73 },
    'F': { color: 0x00ff00, radius: 0.71 },
    'Cl': { color: 0x00ff00, radius: 0.99 },
    'Br': { color: 0x8b0000, radius: 1.14 },
    'I': { color: 0x9400d3, radius: 1.33 },
    'P': { color: 0xffa500, radius: 1.06 },
    'S': { color: 0xffff00, radius: 1.02 },
    'B': { color: 0xff1493, radius: 0.88 },
    'Li': { color: 0xcc80ff, radius: 1.34 },
    'Na': { color: 0xab82ff, radius: 1.54 },
    'K': { color: 0x8f40d4, radius: 1.96 },
    'Ca': { color: 0x3dff00, radius: 1.74 },
    'Fe': { color: 0xffa500, radius: 1.17 },
    'Zn': { color: 0x7d80b0, radius: 1.25 },
    'Cu': { color: 0x1f75cc, radius: 1.17 },
    'Mg': { color: 0x8aff00, radius: 1.45 },
    'Si': { color: 0xdaa520, radius: 1.17 },
    'He': { color: 0xd9ffff, radius: 0.28 },
    'Ne': { color: 0xb3e3f5, radius: 0.38 },
    'Ar': { color: 0x80d1e3, radius: 0.71 },
    'Kr': { color: 0x5cb8d1, radius: 0.88 },
    'Xe': { color: 0x429eb0, radius: 1.08 },
    'Mn': { color: 0x9c7ac7, radius: 1.17 },
    'Ni': { color: 0x50d050, radius: 1.15 },
    'Co': { color: 0xfa9a48, radius: 1.16 },
    'Ag': { color: 0xc0c0c0, radius: 1.34 },
    'Au': { color: 0xffd123, radius: 1.34 }
});

const BOND_LENGTHS = Object.freeze({
    'C-C': 1.54, 'C=C': 1.34, 'C≡C': 1.20,
    'C-H': 1.09, 'C-O': 1.43, 'C=O': 1.20,
    'C-N': 1.47, 'C=N': 1.35, 'C≡N': 1.15,
    'C-S': 1.82, 'C-F': 1.35, 'C-Cl': 1.77,
    'C-Br': 1.94, 'C-I': 2.14, 'N-H': 1.01,
    'O-H': 0.96, 'N-O': 1.44, 'N=O': 1.21,
    'O-O': 1.48, 'N-N': 1.45, 'N=N': 1.25,
    'S-H': 1.34, 'P-O': 1.63, 'P=O': 1.45
});

const CONECT_POSITIONS = Object.freeze([11, 16, 21, 26, 31, 36, 41, 46]);

export class CubeLoader {
    constructor() {
        this.atomData = ATOM_DATA;
    }

    parse(content) {
        const lines = this._splitLines(content);
        let lineIndex = 0;

        lineIndex++;

        lineIndex++;

        const atomCountLine = this._parseNumbers(lines[lineIndex++]);
        const atomCount = Math.abs(atomCountLine[0]);

        const origin = {
            x: atomCountLine[1],
            y: atomCountLine[2],
            z: atomCountLine[3]
        };

        const nxLine = this._parseNumbers(lines[lineIndex++]);
        const nyLine = this._parseNumbers(lines[lineIndex++]);
        const nzLine = this._parseNumbers(lines[lineIndex++]);

        const size = {
            x: Math.abs(nxLine[0]),
            y: Math.abs(nyLine[0]),
            z: Math.abs(nzLine[0])
        };

        const spacing = {
            x: nxLine[1],
            y: nyLine[2],
            z: nzLine[3]
        };

        const atoms = [];
        for (let i = 0; i < atomCount; i++) {
            const atomLine = this._parseNumbers(lines[lineIndex++]);
            const atomicNumber = Math.floor(atomLine[0]);
            const element = this._atomicNumberToSymbol(atomicNumber);
            const elementInfo = ATOM_DATA[element] || ATOM_DATA['C'];

            atoms.push({
                serial: i + 1,
                name: element,
                element: element,
                position: {
                    x: atomLine[2],
                    y: atomLine[3],
                    z: atomLine[4]
                },
                color: elementInfo.color,
                radius: elementInfo.radius
            });
        }

        const voxelCount = size.x * size.y * size.z;
        const volumeData = new Float32Array(voxelCount);
        let voxelIndex = 0;
        let minValue = Infinity;
        let maxValue = -Infinity;

        while (lineIndex < lines.length && voxelIndex < voxelCount) {
            const values = this._parseNumbers(lines[lineIndex++]);
            for (const value of values) {
                if (voxelIndex < voxelCount) {
                    volumeData[voxelIndex] = value;
                    minValue = Math.min(minValue, value);
                    maxValue = Math.max(maxValue, value);
                    voxelIndex++;
                }
            }
        }

        const bonds = [];
        if (atoms.length > 0) {
            this._inferBonds(atoms, bonds);
        }

        return {
            atoms,
            bonds,
            volume: {
                data: volumeData,
                size,
                spacing,
                origin,
                minValue,
                maxValue
            }
        };
    }

    _splitLines(content) {
        return content.split(/\r?\n/);
    }

    _parseNumbers(line) {
        return line.trim().split(/\s+/).map(s => parseFloat(s)).filter(n => !isNaN(n));
    }

    _atomicNumberToSymbol(atomicNumber) {
        const elements = [
            '', 'H', 'He', 'Li', 'Be', 'B', 'C', 'N', 'O', 'F', 'Ne',
            'Na', 'Mg', 'Al', 'Si', 'P', 'S', 'Cl', 'Ar', 'K', 'Ca',
            'Sc', 'Ti', 'V', 'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu', 'Zn',
            'Ga', 'Ge', 'As', 'Se', 'Br', 'Kr', 'Rb', 'Sr', 'Y', 'Zr',
            'Nb', 'Mo', 'Tc', 'Ru', 'Rh', 'Pd', 'Ag', 'Cd', 'In', 'Sn',
            'Sb', 'Te', 'I', 'Xe', 'Cs', 'Ba', 'La', 'Ce', 'Pr', 'Nd',
            'Pm', 'Sm', 'Eu', 'Gd', 'Tb', 'Dy', 'Ho', 'Er', 'Tm', 'Yb',
            'Lu', 'Hf', 'Ta', 'W', 'Re', 'Os', 'Ir', 'Pt', 'Au', 'Hg',
            'Tl', 'Pb', 'Bi', 'Po', 'At', 'Rn'
        ];
        return elements[atomicNumber] || 'C';
    }

    _inferBonds(atoms, bonds) {
        if (atoms.length < 2) return;

        const gridCellSize = 2.5;
        const grid = new Map();
        const maxBondLength = 2.0;
        const tolerance = 0.45;

        for (let i = 0; i < atoms.length; i++) {
            const atom = atoms[i];
            const pos = atom.position;
            const gx = Math.floor(pos.x / gridCellSize);
            const gy = Math.floor(pos.y / gridCellSize);
            const gz = Math.floor(pos.z / gridCellSize);
            const key = `${gx},${gy},${gz}`;
            let cell = grid.get(key);
            if (!cell) {
                cell = [];
                grid.set(key, cell);
            }
            cell.push(i);
        }

        for (let i = 0; i < atoms.length; i++) {
            const atom1 = atoms[i];
            const pos1 = atom1.position;
            const gx = Math.floor(pos1.x / gridCellSize);
            const gy = Math.floor(pos1.y / gridCellSize);
            const gz = Math.floor(pos1.z / gridCellSize);

            for (let dx = -1; dx <= 1; dx++) {
                for (let dy = -1; dy <= 1; dy++) {
                    for (let dz = -1; dz <= 1; dz++) {
                        const key = `${gx + dx},${gy + dy},${gz + dz}`;
                        const cell = grid.get(key);
                        if (!cell) continue;

                        for (const j of cell) {
                            if (j <= i) continue;

                            const atom2 = atoms[j];
                            const pos2 = atom2.position;

                            const dx2 = pos2.x - pos1.x;
                            const dy2 = pos2.y - pos1.y;
                            const dz2 = pos2.z - pos1.z;
                            const distanceSq = dx2 * dx2 + dy2 * dy2 + dz2 * dz2;

                            if (distanceSq > maxBondLength * maxBondLength) continue;

                            const distance = Math.sqrt(distanceSq);
                            const bondKey1 = `${atom1.element}-${atom2.element}`;
                            const bondKey2 = `${atom2.element}-${atom1.element}`;
                            const expectedLength = BOND_LENGTHS[bondKey1] || BOND_LENGTHS[bondKey2] || 1.5;

                            if (distance <= expectedLength + tolerance) {
                                bonds.push({
                                    atom1Index: i,
                                    atom2Index: j,
                                    type: 1
                                });
                            }
                        }
                    }
                }
            }
        }
    }
}

export class PDBLoader {
    parse(content) {
        const atoms = [];
        const bonds = [];
        const atomMap = new Map();

        let lineStart = 0;
        let lineEnd = content.indexOf('\n');

        while (lineEnd !== -1) {
            this.processLine(content, lineStart, lineEnd, atoms, atomMap, bonds);
            lineStart = lineEnd + 1;
            lineEnd = content.indexOf('\n', lineStart);
        }

        if (lineStart < content.length) {
            this.processLine(content, lineStart, content.length, atoms, atomMap, bonds);
        }

        if (bonds.length === 0 && atoms.length > 0) {
            this.inferBondsOptimized(atoms, bonds);
        }

        return { atoms, bonds };
    }

    processLine(content, start, end, atoms, atomMap, bonds) {
        const firstChar = content.charAt(start);

        if (firstChar === 'A' && content.startsWith('ATOM', start)) {
            const atom = this.parseAtomLine(content, start, end);
            if (atom) {
                atoms.push(atom);
                atomMap.set(atom.serial, atoms.length - 1);
            }
        } else if (firstChar === 'H' && content.startsWith('HETATM', start)) {
            const atom = this.parseAtomLine(content, start, end);
            if (atom) {
                atoms.push(atom);
                atomMap.set(atom.serial, atoms.length - 1);
            }
        } else if (firstChar === 'C' && content.startsWith('CONECT', start)) {
            this.parseConectLine(content, start, end, atomMap, bonds);
        }
    }

    parseAtomLine(content, start, end) {
        try {
            const serial = parseInt(this.substrTrim(content, start + 6, start + 11)) || 0;
            const name = this.substrTrim(content, start + 12, start + 16);
            const element = this.substrTrim(content, start + 76, Math.min(start + 78, end));
            let actualElement = element;

            if (!actualElement) {
                actualElement = this.guessElementFromName(name);
            }

            const x = parseFloat(this.substrTrim(content, start + 30, start + 38)) || 0;
            const y = parseFloat(this.substrTrim(content, start + 38, start + 46)) || 0;
            const z = parseFloat(this.substrTrim(content, start + 46, start + 54)) || 0;

            const elementInfo = ATOM_DATA[actualElement] || ATOM_DATA['C'];

            return {
                serial,
                name,
                element: actualElement,
                position: { x, y, z },
                color: elementInfo.color,
                radius: elementInfo.radius
            };
        } catch (error) {
            console.warn('解析原子行失败:', content.substring(start, end), error);
            return null;
        }
    }

    substrTrim(content, start, end) {
        while (start < end && content.charAt(start) === ' ') start++;
        while (end > start && content.charAt(end - 1) === ' ') end--;
        return content.substring(start, end);
    }

    guessElementFromName(name) {
        const firstChar = name.charAt(0);
        const secondChar = name.charAt(1);

        const twoLetter = firstChar + secondChar;
        if (ATOM_DATA[twoLetter]) {
            return twoLetter;
        }

        if (ATOM_DATA[firstChar]) {
            return firstChar;
        }

        return 'C';
    }

    parseConectLine(content, start, end, atomMap, bonds) {
        const atom1Str = this.substrTrim(content, start + 6, start + 11);
        const atom1 = parseInt(atom1Str);
        if (isNaN(atom1)) return;

        const atom1Index = atomMap.get(atom1);
        if (atom1Index === undefined) return;

        for (const pos of CONECT_POSITIONS) {
            const posStart = start + pos;
            const posEnd = posStart + 5;
            if (posEnd > end) break;

            const atom2Str = this.substrTrim(content, posStart, posEnd);
            if (!atom2Str) continue;

            const atom2 = parseInt(atom2Str);
            if (isNaN(atom2) || atom1 === atom2) continue;

            const atom2Index = atomMap.get(atom2);
            if (atom2Index === undefined) continue;

            if (atom1Index < atom2Index) {
                bonds.push({
                    atom1Index,
                    atom2Index,
                    type: 1
                });
            }
        }
    }

    inferBondsOptimized(atoms, bonds) {
        if (atoms.length < 2) return;

        const gridCellSize = 2.5;
        const grid = new Map();
        const maxBondLength = 2.0;
        const tolerance = 0.45;

        for (let i = 0; i < atoms.length; i++) {
            const atom = atoms[i];
            const pos = atom.position;

            const gx = Math.floor(pos.x / gridCellSize);
            const gy = Math.floor(pos.y / gridCellSize);
            const gz = Math.floor(pos.z / gridCellSize);

            const key = `${gx},${gy},${gz}`;
            let cell = grid.get(key);
            if (!cell) {
                cell = [];
                grid.set(key, cell);
            }
            cell.push(i);
        }

        for (let i = 0; i < atoms.length; i++) {
            const atom1 = atoms[i];
            const pos1 = atom1.position;

            const gx = Math.floor(pos1.x / gridCellSize);
            const gy = Math.floor(pos1.y / gridCellSize);
            const gz = Math.floor(pos1.z / gridCellSize);

            for (let dx = -1; dx <= 1; dx++) {
                for (let dy = -1; dy <= 1; dy++) {
                    for (let dz = -1; dz <= 1; dz++) {
                        const key = `${gx + dx},${gy + dy},${gz + dz}`;
                        const cell = grid.get(key);
                        if (!cell) continue;

                        for (const j of cell) {
                            if (j <= i) continue;

                            const atom2 = atoms[j];
                            const pos2 = atom2.position;

                            const dx2 = pos2.x - pos1.x;
                            const dy2 = pos2.y - pos1.y;
                            const dz2 = pos2.z - pos1.z;
                            const distanceSq = dx2 * dx2 + dy2 * dy2 + dz2 * dz2;

                            if (distanceSq > maxBondLength * maxBondLength) continue;

                            const distance = Math.sqrt(distanceSq);

                            const bondKey1 = `${atom1.element}-${atom2.element}`;
                            const bondKey2 = `${atom2.element}-${atom1.element}`;
                            const expectedLength = BOND_LENGTHS[bondKey1] || BOND_LENGTHS[bondKey2] || 1.5;

                            if (distance <= expectedLength + tolerance) {
                                bonds.push({
                                    atom1Index: i,
                                    atom2Index: j,
                                    type: 1
                                });
                            }
                        }
                    }
                }
            }
        }
    }
}
