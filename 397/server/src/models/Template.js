const mongoose = require('mongoose');

const templateSchema = new mongoose.Schema({
  title: {
    type: String,
    required: true,
    trim: true,
    maxlength: 100
  },
  description: {
    type: String,
    required: true,
    maxlength: 2000
  },
  category: {
    type: String,
    enum: ['operation', 'sales', 'finance', 'ops'],
    required: true
  },
  thumbnail: {
    type: String,
    required: true
  },
  previewImages: [{
    type: String
  }],
  fileUrl: {
    type: String,
    default: ''
  },
  author: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'User',
    required: true
  },
  price: {
    type: Number,
    default: 0,
    min: 0
  },
  rating: {
    type: Number,
    default: 0,
    min: 0,
    max: 5
  },
  ratingCount: {
    type: Number,
    default: 0
  },
  downloadCount: {
    type: Number,
    default: 0
  },
  viewCount: {
    type: Number,
    default: 0
  },
  tags: [{
    type: String,
    trim: true
  }],
  complexity: {
    type: String,
    enum: ['simple', 'medium', 'complex'],
    default: 'medium'
  },
  components: [{
    id: String,
    type: {
      type: String,
      enum: ['chart', 'metric', 'table', 'text', 'image']
    },
    chartType: {
      type: String,
      enum: ['line', 'bar', 'pie', 'area', 'gauge']
    },
    title: String,
    position: {
      x: Number,
      y: Number
    },
    size: {
      w: Number,
      h: Number
    },
    config: mongoose.Schema.Types.Mixed,
    dataSource: {
      type: {
        type: String,
        enum: ['static', 'api', 'database']
      },
      data: mongoose.Schema.Types.Mixed,
      apiUrl: String,
      fields: [{
        sourceField: String,
        targetField: String,
        label: String
      }]
    }
  }],
  layout: {
    gridCols: {
      type: Number,
      default: 12
    },
    gridRows: {
      type: Number,
      default: 8
    },
    gutter: {
      type: Number,
      default: 16
    },
    backgroundColor: {
      type: String,
      default: '#0F172A'
    }
  },
  version: {
    type: String,
    default: '1.0.0'
  },
  status: {
    type: String,
    enum: ['pending', 'approved', 'rejected'],
    default: 'pending'
  },
  reviewNote: {
    type: String,
    default: ''
  },
  rejectReason: {
    type: String,
    default: ''
  },
  reviewedAt: {
    type: Date
  },
  reviewedBy: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'User'
  },
  createdAt: {
    type: Date,
    default: Date.now
  },
  updatedAt: {
    type: Date,
    default: Date.now
  }
});

templateSchema.index({ category: 1 });
templateSchema.index({ author: 1 });
templateSchema.index({ status: 1 });
templateSchema.index({ rating: -1 });
templateSchema.index({ downloadCount: -1 });
templateSchema.index({ createdAt: -1 });
templateSchema.index({ tags: 1 });
templateSchema.index({ title: 'text', description: 'text' });

templateSchema.pre('save', function() {
  this.updatedAt = Date.now();
});

module.exports = mongoose.model('Template', templateSchema);
