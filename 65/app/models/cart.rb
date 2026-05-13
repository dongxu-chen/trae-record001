class Cart < ApplicationRecord
  belongs_to :coupon, optional: true

  has_many :cart_items, dependent: :destroy
  has_many :products, through: :cart_items

  def subtotal
    cart_items.joins(:product).sum('cart_items.quantity * products.price')
  end

  def discount_amount
    return 0 unless coupon

    coupon.calculate_discount(subtotal)
  end

  def total_price
    [subtotal - discount_amount, 0].max
  end

  def apply_coupon(coupon_code)
    with_lock do
      coupon = Coupon.find_by(code: coupon_code.upcase)
      return { success: false, error: 'Coupon not found' } unless coupon
      return { success: false, error: 'Coupon is invalid for this cart' } unless coupon.valid_for_cart?(self)

      update!(coupon: coupon)
      { success: true, discount: discount_amount, total: total_price }
    end
  end

  def remove_coupon
    with_lock do
      update!(coupon: nil)
      { success: true, total: total_price }
    end
  end

  def add_product(product, quantity = 1)
    with_lock do
      cart_item = cart_items.find_or_initialize_by(product_id: product.id)
      cart_item.quantity = (cart_item.quantity || 0) + quantity
      cart_item.save!
    end
  end

  def remove_product(product)
    with_lock do
      cart_items.find_by(product_id: product.id)&.destroy
    end
  end

  def update_quantity(product, quantity)
    with_lock do
      cart_item = cart_items.find_by(product_id: product.id)
      return unless cart_item

      if quantity > 0
        cart_item.update!(quantity: quantity)
      else
        cart_item.destroy
      end
    end
  end

  def empty?
    cart_items.empty?
  end

  def items_count
    cart_items.sum(:quantity)
  end
end
