class CartsController < ApplicationController
  before_action :set_cart, only: [:show, :destroy]

  def create
    @cart = Cart.new(cart_params)

    if @cart.save
      render json: @cart, status: :created, location: @cart
    else
      render json: @cart.errors, status: :unprocessable_entity
    end
  end

  def show
    @cart.with_lock do
      @cart.reload
      render json: @cart, include: [:cart_items, :products], methods: [:total_price]
    end
  end

  def destroy
    @cart.destroy
    head :no_content
  end

  private

  def set_cart
    @cart = Cart.find(params[:id])
  end

  def cart_params
    params.fetch(:cart, {}).permit(:user_id)
  end
end
