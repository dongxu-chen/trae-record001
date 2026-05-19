const mongoose = require('mongoose');

const modelSchema = new mongoose.Schema({
  name: {
    type: String,
    required: true
  },
  description: String,
  fileType: {
    type: String,
    enum: ['gltf', 'glb', 'obj'],
    required: true
  },
  filePath: {
    type: String,
    required: true
  },
  materials: [{
    name: String,
    albedoColor: { r: Number, g: Number, b: Number },
    metallic: Number,
    roughness: Number,
    emissiveColor: { r: Number, g: Number, b: Number },
    emissiveIntensity: Number
  }],
  animations: [{
    name: String,
    duration: Number
  }],
  createdAt: {
    type: Date,
    default: Date.now
  }
});

module.exports = mongoose.model('Model', modelSchema);
