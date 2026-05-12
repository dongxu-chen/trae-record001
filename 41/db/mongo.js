const mongoose = require('mongoose');

const bookSchema = new mongoose.Schema({
  title: { type: String, required: true },
  author: { type: String, required: true },
  isbn: { type: String, required: true, unique: true },
  publishedYear: { type: Number, required: true },
  totalCopies: { type: Number, required: true },
  availableCopies: { type: Number, required: true }
});

const userSchema = new mongoose.Schema({
  name: { type: String, required: true },
  email: { type: String, required: true, unique: true }
});

const borrowRecordSchema = new mongoose.Schema({
  userId: { type: mongoose.Schema.Types.ObjectId, ref: 'User', required: true },
  bookId: { type: mongoose.Schema.Types.ObjectId, ref: 'Book', required: true },
  borrowDate: { type: Date, required: true },
  returnDate: { type: Date },
  isReturned: { type: Boolean, required: true, default: false }
});

const Book = mongoose.model('Book', bookSchema);
const User = mongoose.model('User', userSchema);
const BorrowRecord = mongoose.model('BorrowRecord', borrowRecordSchema);

async function connectDB() {
  try {
    await mongoose.connect('mongodb://localhost:27017/library', {
      maxPoolSize: 10,
      serverSelectionTimeoutMS: 5000,
      socketTimeoutMS: 45000
    });
    console.log('MongoDB connected successfully');
  } catch (error) {
    console.error('MongoDB connection error:', error);
    process.exit(1);
  }
}

async function closeDB() {
  try {
    await mongoose.connection.close();
    console.log('MongoDB connection closed');
  } catch (error) {
    console.error('Error closing MongoDB connection:', error);
  }
}

module.exports = {
  connectDB,
  closeDB,
  Book,
  User,
  BorrowRecord
};
