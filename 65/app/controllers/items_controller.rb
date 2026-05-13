class ItemsController < ApplicationController
  before_action :set_cart
  before_action :set_product, only: [:create, :update, :destroy]

  def create
    quantity = params[:quantity] || 1

    begin
      @cart.add_product(@product, quantity.to_i)
      @cart.reload
      render json: @cart, include: [:cart_items, :products], methods: [:total_price], status: :created
    rescue ActiveRecord::RecordInvalid => e
      render json: { error: e.message }, status: :unprocessable_entity
    end
  end

  def update
    quantity = params[:quantity].to_i

    if quantity >= 0
      @cart.update_quantity(@product, quantity)
      @cart.reload
      render json: @cart, include: [:cart_items, :products], methods: [:total_price]
    else
      render json: { error: 'Quantity must be non-negative' }, status: :unprocessable_entity
    end
  end

  def destroy
    @cart.remove_product(@product)
    head :no_content
  end

  private

  def set_cart
    @cart = Cart.find(params[:cart_id])
  end

  def set_product
    @product = Product.find(params[:product_id])
  end
end
