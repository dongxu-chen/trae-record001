class OrdersController < ApplicationController
  before_action :set_order, only: [:show, :pay, :cancel]

  def index
    @orders = Order.all.order(created_at: :desc)
    render json: @orders, include: [:order_items]
  end

  def show
    render json: @order, include: [:order_items, :coupon]
  end

  def checkout
    @cart = Cart.find(params[:cart_id])

    result = Order.create_from_cart(@cart, params[:user_id])

    if result[:success]
      @order = result[:order]
      OrderTimeoutJob.set(wait_until: @order.payment_expires_at).perform_later(@order.id)
      render json: @order, include: [:order_items, :coupon], status: :created, location: @order
    else
      render json: { error: result[:error] }, status: :unprocessable_entity
    end
  end

  def pay
    result = @order.mark_as_paid

    if result[:success]
      render json: @order, include: [:order_items, :coupon]
    else
      render json: { error: result[:error] }, status: :unprocessable_entity
    end
  end

  def cancel
    result = @order.cancel(params[:reason])

    if result[:success]
      render json: @order, include: [:order_items, :coupon]
    else
      render json: { error: result[:error] }, status: :unprocessable_entity
    end
  end

  def apply_coupon
    @cart = Cart.find(params[:cart_id])
    result = @cart.apply_coupon(params[:coupon_code])

    if result[:success]
      render json: {
        success: true,
        coupon: @cart.coupon,
        subtotal: @cart.subtotal,
        discount: result[:discount],
        total: result[:total]
      }
    else
      render json: { success: false, error: result[:error] }, status: :unprocessable_entity
    end
  end

  def remove_coupon
    @cart = Cart.find(params[:cart_id])
    result = @cart.remove_coupon

    render json: {
      success: true,
      subtotal: @cart.subtotal,
      discount: 0,
      total: result[:total]
    }
  end

  private

  def set_order
    @order = Order.find(params[:id])
  end
end
