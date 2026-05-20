const express = require('express');
const router = express.Router();
const multer = require('multer');
const path = require('path');
const fs = require('fs');
const Model = require('../models/Model');

const uploadDir = path.join(__dirname, '../../uploads');
const exportDir = path.join(__dirname, '../../exports');
const texturesDir = path.join(exportDir, 'textures');

[uploadDir, exportDir, texturesDir].forEach(dir => {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
});

const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    cb(null, uploadDir);
  },
  filename: (req, file, cb) => {
    const uniqueSuffix = Date.now() + '-' + Math.round(Math.random() * 1E9);
    cb(null, uniqueSuffix + path.extname(file.originalname));
  }
});

const upload = multer({
  storage: storage,
  fileFilter: (req, file, cb) => {
    const allowedTypes = ['.gltf', '.glb', '.obj', '.bin', '.mtl'];
    const ext = path.extname(file.originalname).toLowerCase();
    if (allowedTypes.includes(ext)) {
      cb(null, true);
    } else {
      cb(new Error('Invalid file type. Only glTF, GLB, and OBJ files are allowed.'));
    }
  }
});

router.get('/', async (req, res) => {
  try {
    const models = await Model.find().sort({ createdAt: -1 });
    res.json(models);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

router.get('/:id', async (req, res) => {
  try {
    const model = await Model.findById(req.params.id);
    if (!model) {
      return res.status(404).json({ error: 'Model not found' });
    }
    res.json(model);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

router.post('/upload', upload.single('model'), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ error: 'No file uploaded' });
    }

    const ext = path.extname(req.file.originalname).toLowerCase();
    let fileType = 'gltf';
    if (ext === '.glb') fileType = 'glb';
    if (ext === '.obj') fileType = 'obj';

    const model = new Model({
      name: req.body.name || req.file.originalname,
      description: req.body.description || '',
      fileType: fileType,
      filePath: `/uploads/${req.file.filename}`
    });

    await model.save();
    res.status(201).json(model);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

router.put('/:id', async (req, res) => {
  try {
    const model = await Model.findByIdAndUpdate(
      req.params.id,
      req.body,
      { new: true }
    );
    if (!model) {
      return res.status(404).json({ error: 'Model not found' });
    }
    res.json(model);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

router.delete('/:id', async (req, res) => {
  try {
    const model = await Model.findById(req.params.id);
    if (!model) {
      return res.status(404).json({ error: 'Model not found' });
    }

    const filePath = path.join(__dirname, '../..', model.filePath);
    if (fs.existsSync(filePath)) {
      fs.unlinkSync(filePath);
    }

    await Model.findByIdAndDelete(req.params.id);
    res.json({ message: 'Model deleted successfully' });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

router.post('/:id/export-gltf', async (req, res) => {
  try {
    const { sceneData, textures, animations, morphTargets } = req.body;
    const model = await Model.findById(req.params.id);
    if (!model) {
      return res.status(404).json({ error: 'Model not found' });
    }

    const exportId = `export_${Date.now()}`;
    const modelExportDir = path.join(exportDir, exportId);
    const modelTexturesDir = path.join(modelExportDir, 'textures');
    
    fs.mkdirSync(modelExportDir, { recursive: true });
    fs.mkdirSync(modelTexturesDir, { recursive: true });

    const textureFiles = [];
    if (textures && textures.length > 0) {
      textures.forEach((tex, index) => {
        const textureFileName = `texture_${index}${tex.extension || '.png'}`;
        const texturePath = path.join(modelTexturesDir, textureFileName);
        
        if (tex.base64) {
          const base64Data = tex.base64.replace(/^data:image\/\w+;base64,/, '');
          fs.writeFileSync(texturePath, base64Data, 'base64');
        }
        
        textureFiles.push({
          name: tex.name || textureFileName,
          uri: `textures/${textureFileName}`,
          type: tex.type
        });
      });
    }

    const gltf = {
      asset: {
        version: '2.0',
        generator: '3D Model Editor',
        copyright: model.name
      },
      scene: 0,
      scenes: [{ name: model.name, nodes: [0] }],
      nodes: [{
        name: model.name,
        mesh: 0,
        translation: [0, 0, 0],
        rotation: [0, 0, 0, 1],
        scale: [1, 1, 1]
      }],
      meshes: [{
        name: `${model.name}_mesh`,
        primitives: sceneData.primitives || [{
          attributes: { POSITION: 0 },
          indices: 1,
          material: 0
        }]
      }],
      materials: sceneData.materials || [{
        name: 'default_material',
        pbrMetallicRoughness: {
          baseColorFactor: [1, 1, 1, 1],
          metallicFactor: 0,
          roughnessFactor: 0.5
        }
      }],
      textures: textureFiles.map((tex, i) => ({
        sampler: 0,
        source: i,
        name: tex.name
      })),
      images: textureFiles.map(tex => ({
        uri: tex.uri,
        name: tex.name
      })),
      samplers: [{
        magFilter: 9729,
        minFilter: 9987,
        wrapS: 10497,
        wrapT: 10497
      }],
      accessors: sceneData.accessors || [],
      bufferViews: sceneData.bufferViews || [],
      buffers: sceneData.buffers || []
    };

    if (animations && animations.length > 0) {
      gltf.animations = animations.map((anim, i) => ({
        name: anim.name || `animation_${i}`,
        channels: anim.channels || [],
        samplers: (anim.samplers || []).map(s => ({
          ...s,
          interpolation: 'LINEAR'
        }))
      }));
    }

    if (morphTargets && morphTargets.length > 0) {
      gltf.meshes[0].weights = morphTargets.map(mt => mt.initialWeight || 0);
      gltf.meshes[0].primitives[0].targets = morphTargets.map(mt => mt.attributes);
    }

    const gltfPath = path.join(modelExportDir, 'model.gltf');
    fs.writeFileSync(gltfPath, JSON.stringify(gltf, null, 2));

    res.json({
      exportId,
      gltfUrl: `/exports/${exportId}/model.gltf`,
      textures: textureFiles,
      message: 'glTF exported successfully with external textures'
    });
  } catch (err) {
    console.error('Export error:', err);
    res.status(500).json({ error: err.message });
  }
});

module.exports = router;
