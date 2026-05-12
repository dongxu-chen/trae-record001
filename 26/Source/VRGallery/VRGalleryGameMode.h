#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "VRGalleryGameMode.generated.h"

UCLASS()
class VRGALLERY_API AVRGalleryGameMode : public AGameModeBase
{
	GENERATED_BODY()

public:
	AVRGalleryGameMode();

protected:
	virtual void BeginPlay() override;

public:
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "VR Gallery")
	TSubclassOf<class AVRPawn> VRPawnClass;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "VR Gallery")
	TSubclassOf<class AUIManager> UIManagerClass;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "VR Gallery")
	class AUIManager* UIManagerInstance;

	UFUNCTION(BlueprintCallable, Category = "VR Gallery")
	void SpawnUIManager();
};
