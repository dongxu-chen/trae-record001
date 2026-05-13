class OrderTimeoutJob < ApplicationJob
  queue_as :default

  def perform(order_id)
    order = Order.find_by(id: order_id)
    return unless order

    order.cancel_if_expired
  end
end
