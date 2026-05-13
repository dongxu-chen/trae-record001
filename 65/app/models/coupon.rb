class Coupon < ApplicationRecord
  has_many :carts, dependent: :nullify
  has_many :orders, dependent: :nullify

  enum discount_type: { fixed_amount: 0, percentage: 1 }

  validates :code, presence: true, uniqueness: true
  validates :discount_type, presence: true
  validates :discount_value, presence: true, numericality: { greater_than: 0 }
  validates :min_order_amount, numericality: { greater_than_or_equal_to: 0 }, allow_nil: true
  validates :max_uses, numericality: { only_integer: true, greater_than: 0 }, allow_nil: true
  validates :used_count, numericality: { only_integer: true, greater_than_or_equal_to: 0 }
  validates :expires_at, presence: true

  def valid_for_cart?(cart)
    return false unless active?
    return false if expired?
    return false if max_uses_reached?
    return false if min_order_amount && cart.subtotal < min_order_amount

    true
  end

  def active?
    is_active
  end

  def expired?
    expires_at < Time.current
  end

  def max_uses_reached?
    max_uses && used_count >= max_uses
  end

  def calculate_discount(amount)
    return 0 unless active? && !expired?

    case discount_type
    when 'fixed_amount'
      [discount_value, amount].min
    when 'percentage'
      (amount * discount_value / 100.0).round(2)
    else
      0
    end
  end

  def increment_used_count!
    with_lock do
      increment!(:used_count)
    end
  end
end
