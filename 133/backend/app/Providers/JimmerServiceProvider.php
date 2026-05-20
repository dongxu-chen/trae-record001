<?php

namespace App\Providers;

use Illuminate\Support\ServiceProvider;
use App\Jimmer\JimmerConfig;
use App\Jimmer\EntityManager;

class JimmerServiceProvider extends ServiceProvider
{
    public function register()
    {
        $this->app->singleton(JimmerConfig::class, function ($app) {
            return JimmerConfig::create()
                ->setConnectionName('tenant')
                ->enableEncryption(true)
                ->setEncryptionKey(env('JIMMER_ENCRYPTION_KEY', env('APP_KEY')))
                ->enableOptimization(true)
                ->addEntityPath(app_path('Jimmer/Entity'), 'App\Jimmer\Entity');
        });
        
        $this->app->singleton(EntityManager::class, function ($app) {
            return EntityManager::getInstance($app->make(JimmerConfig::class));
        });
    }
    
    public function boot()
    {
    }
}
