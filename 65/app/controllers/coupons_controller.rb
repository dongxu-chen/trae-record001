class CouponsController < ApplicationController
  before_action :set_coupon, only: [:show, :update, :destroy]

  def index
    @coupons = Coupon.all
    render json: @coupons
  end

  def show
    render json: @coupon
  end

  def create
    @coupon = Coupon.new(coupon_params)
    @coupon.code = @coupon.code.upcase if @coupon.code

    if @coupon.save
      render json: @coupon, status: :created, location: @coupon
    else
      render json: @coupon.errors, status: :unprocessable_entity
    end
  end

  def update
    if @coupon.update(coupon_params)
      render json: @coupon
    else
      render json: @coupon.errors, status: :unprocessable_entity
    end
  end

  def destroy
    @coupon.destroy
    head :no_content
  end

  private

  def set_coupon
    @coupon = Coupon.find(params[:id])
  end

  def coupon_params
    params.require(:coupon).permit(
      :code,
      :discount_type,
      :discount_value,
      :min_order_amount,
      :max_uses,
      :is_active,
      :expires_at
    )
  end
end
