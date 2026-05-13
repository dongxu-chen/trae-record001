class Product < ApplicationRecord
  has_many :cart_items
  has_many :carts, through: :cart_items

  validates :name, presence: true
  validates :price, presence: true, numericality: { greater_than_or_equal_to: 0 }
end
