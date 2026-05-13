Rails.application.routes.draw do
  resources :carts, only: [:create, :show, :destroy] do
    resources :items, controller: 'items', only: [:create, :update, :destroy], param: :product_id
    post 'apply_coupon', on: :member, to: 'orders#apply_coupon'
    delete 'remove_coupon', on: :member, to: 'orders#remove_coupon'
    post 'checkout', on: :member, to: 'orders#checkout'
  end

  resources :products, only: [:index, :show, :create, :update, :destroy]

  resources :coupons, only: [:index, :show, :create, :update, :destroy]

  resources :orders, only: [:index, :show] do
    post 'pay', on: :member
    post 'cancel', on: :member
  end
end
