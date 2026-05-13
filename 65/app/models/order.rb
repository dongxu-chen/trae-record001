class Order < ApplicationRecord
  belongs_to :cart
  belongs_to :coupon, optional: true

  has_many :order_items, dependent: :destroy

  enum status: {
    pending: 0,
    paid: 1,
    shipped: 2,
    delivered: 3,
    cancelled: 4
  }

  validates :order_number, presence: true, uniqueness: true
  validates :subtotal, presence: true, numericality: { greater_than_or_equal_to: 0 }
  validates :discount_amount, presence: true, numericality: { greater_than_or_equal_to: 0 }
  validates :total_price, presence: true, numericality: { greater_than_or_equal_to: 0 }
  validates :status, presence: true

  before_validation :generate_order_number, on: :create

  PAYMENT_TIMEOUT = 30.minutes

  def self.create_from_cart(cart, user_id = nil)
    return { success: false, error: 'Cart is empty' } if cart.empty?

    transaction do
      if cart.coupon && !cart.coupon.valid_for_cart?(cart)
        return { success: false, error: 'Coupon is no longer valid' }
      end

      order = Order.new(
        cart: cart,
        coupon: cart.coupon,
        user_id: user_id,
        subtotal: cart.subtotal,
        discount_amount: cart.discount_amount,
        total_price: cart.total_price,
        status: :pending,
        payment_expires_at: Time.current + PAYMENT_TIMEOUT
      )

      if order.save
        cart.cart_items.each do |cart_item|
          order.order_items.create!(
            product_id: cart_item.product_id,
            product_name: cart_item.product.name,
            product_price: cart_item.product.price,
            quantity: cart_item.quantity,
            subtotal: cart_item.quantity * cart_item.product.price
          )
        end

        if cart.coupon
          cart.coupon.increment_used_count!
        end

        { success: true, order: order }
      else
        { success: false, error: order.errors.full_messages.join(', ') }
      end
    end
  end

  def mark_as_paid
    with_lock do
      return { success: false, error: 'Order is not pending' } unless pending?
      return { success: false, error: 'Payment has expired' } if payment_expired?

      update!(status: :paid, paid_at: Time.current)
      { success: true, order: self }
    end
  end

  def cancel(reason = nil)
    with_lock do
      return { success: false, error: 'Cannot cancel paid or shipped order' } if paid? || shipped? || delivered?
      return { success: false, error: 'Order already cancelled' } if cancelled?

      if coupon
        coupon.with_lock do
          coupon.decrement!(:used_count)
        end
      end

      update!(status: :cancelled, cancelled_at: Time.current, cancel_reason: reason)
      { success: true, order: self }
    end
  end

  def payment_expired?
    return false unless pending?

    payment_expires_at && payment_expires_at < Time.current
  end

  def cancel_if_expired
    if pending? && payment_expired?
      cancel('Payment timeout')
    end
  end

  private

  def generate_order_number
    return if order_number.present?

    loop do
      self.order_number = "ORD#{Time.current.strftime('%Y%m%d%H%M%S')}#{SecureRandom.hex(4).upcase}"
      break unless Order.exists?(order_number: order_number)
    end
  end
end
