const mongoose = require('mongoose');

const taskSchema = new mongoose.Schema({
  name: {
    type: String,
    required: true,
    trim: true
  },
  description: {
    type: String,
    trim: true
  },
  entityTypes: [{
    label: String,
    color: String,
    description: String
  }],
  relationTypes: [{
    label: String,
    color: String,
    description: String
  }],
  eventTypes: [{
    label: String,
    color: String,
    description: String,
    roleTypes: [{
      role: String,
      description: String
    }]
  }],
  createdAt: {
    type: Date,
    default: Date.now
  },
  updatedAt: {
    type: Date,
    default: Date.now
  }
});

module.exports = mongoose.model('Task', taskSchema);
