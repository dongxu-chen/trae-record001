#include "VRGalleryGameMode.h"
#include "VRPawn.h"
#include "UIManager.h"
#include "Kismet/GameplayStatics.h"

AVRGalleryGameMode::AVRGalleryGameMode()
{
	DefaultPawnClass = AVRPawn::StaticClass();
	UIManagerInstance = nullptr;
}

void AVRGalleryGameMode::BeginPlay()
{
	Super::BeginPlay();

	SpawnUIManager();
}

void AVRGalleryGameMode::SpawnUIManager()
{
	if (!UIManagerClass) return;

	UIManagerInstance = GetWorld()->SpawnActor<AUIManager>(UIManagerClass, FVector::ZeroVector, FRotator::ZeroRotator);
}
