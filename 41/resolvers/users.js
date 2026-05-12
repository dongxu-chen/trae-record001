const { User, Book, BorrowRecord } = require('../db/mongo');

module.exports = {
  Query: {
    users: async (parent, { limit = 20, offset = 0 }) => {
      return await User.find().skip(offset).limit(Math.min(limit, 100));
    },
    user: async (parent, { id }) => {
      return await User.findById(id);
    },
    borrowRecords: async (parent, { limit = 20, offset = 0 }) => {
      return await BorrowRecord.find().skip(offset).limit(Math.min(limit, 100));
    },
    borrowRecord: async (parent, { id }) => {
      return await BorrowRecord.findById(id);
    }
  },
  Mutation: {
    createUser: async (parent, { name, email }) => {
      const user = new User({ name, email });
      return await user.save();
    },
    borrowBook: async (parent, { userId, bookId }) => {
      const book = await Book.findById(bookId);
      if (!book) {
        throw new Error('Book not found');
      }
      if (book.availableCopies <= 0) {
        throw new Error('No available copies of this book');
      }

      book.availableCopies -= 1;
      await book.save();

      const borrowRecord = new BorrowRecord({
        userId,
        bookId,
        borrowDate: new Date(),
        isReturned: false
      });
      return await borrowRecord.save();
    },
    returnBook: async (parent, { borrowRecordId }) => {
      const borrowRecord = await BorrowRecord.findById(borrowRecordId);
      if (!borrowRecord) {
        throw new Error('Borrow record not found');
      }
      if (borrowRecord.isReturned) {
        throw new Error('Book already returned');
      }

      borrowRecord.isReturned = true;
      borrowRecord.returnDate = new Date();
      await borrowRecord.save();

      const book = await Book.findById(borrowRecord.bookId);
      if (book) {
        book.availableCopies += 1;
        await book.save();
      }

      return borrowRecord;
    }
  },
  User: {
    borrowRecords: async (user) => {
      return await BorrowRecord.find({ userId: user._id });
    }
  },
  BorrowRecord: {
    book: async (record) => {
      return await Book.findById(record.bookId);
    }
  }
};
