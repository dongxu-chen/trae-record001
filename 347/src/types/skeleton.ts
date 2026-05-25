export interface BoneNode {
  uuid: string;
  name: string;
  parentUuid: string | null;
  children: string[];
  position: [number, number, number];
  rotation: [number, number, number, number];
  scale: [number, number, number];
  boneIndex: number;
}
