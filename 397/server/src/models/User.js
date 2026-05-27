const mongoose = require('mongoose');
const bcrypt = require('bcryptjs');

const userSchema = new mongoose.Schema({
  username: {
    type: String,
    required: true,
    unique: true,
    trim: true,
    minlength: 3,
    maxlength: 20
  },
  email: {
    type: String,
    required: true,
    unique: true,
    trim: true,
    lowercase: true
  },
  password: {
    type: String,
    required: true,
    minlength: 6
  },
  avatar: {
    type: String,
    default: ''
  },
  role: {
    type: String,
    enum: ['user', 'creator', 'admin'],
    default: 'user'
  },
  bio: {
    type: String,
    default: '',
    maxlength: 500
  },
  createdAt: {
    type: Date,
    default: Date.now
  }
});

userSchema.pre('save', function() {
  if (!this.isModified('password')) return Promise.resolve();
  return bcrypt.hash(this.password, 10).then(hash => {
    this.password = hash;
    return Promise.resolve();
  });
});

userSchema.methods.comparePassword = async function(candidatePassword) {
  return bcrypt.compare(candidatePassword, this.password);
};

userSchema.methods.toJSON = function() {
  const user = this.toObject();
  delete user.password;
  return user;
};

module.exports = mongoose.model('User', userSchema);
