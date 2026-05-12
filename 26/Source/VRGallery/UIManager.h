#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "UIManager.generated.h"

class UWidgetComponent;
class UUserWidget;
class AVRPawn;

UENUM(BlueprintType)
enum class EUIType : uint8
{
	MainMenu,
	ExhibitInfo,
	Settings,
	NavigationMap,
	Help
};

USTRUCT(BlueprintType)
struct FUIWidgetConfig
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite)
	TSubclassOf<UUserWidget> WidgetClass;

	UPROPERTY(EditAnywhere, BlueprintReadWrite)
	FVector Location;

	UPROPERTY(EditAnywhere, BlueprintReadWrite)
	FRotator Rotation;

	UPROPERTY(EditAnywhere, BlueprintReadWrite)
	FVector2D DrawSize;

	UPROPERTY(EditAnywhere, BlueprintReadWrite)
	bool bFollowPlayer;

	UPROPERTY(EditAnywhere, BlueprintReadWrite)
	float FollowDistance;
};

UCLASS()
class VRGALLERY_API AUIManager : public AActor
{
	GENERATED_BODY()

public:
	AUIManager();

protected:
	virtual void BeginPlay() override;

public:
	virtual void Tick(float DeltaTime) override;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "UI Configuration")
	TMap<EUIType, FUIWidgetConfig> UIConfigurations;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "UI Settings")
	bool bAutoShowMainMenuOnStart;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "UI Settings")
	float UIFadeDuration;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "UI State")
	EUIType CurrentVisibleUIType;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "UI State")
	bool bAnyUIVisible;

	UFUNCTION(BlueprintCallable, Category = "UI Management")
	void ShowUI(EUIType UIType);

	UFUNCTION(BlueprintCallable, Category = "UI Management")
	void HideUI(EUIType UIType);

	UFUNCTION(BlueprintCallable, Category = "UI Management")
	void ToggleUI(EUIType UIType);

	UFUNCTION(BlueprintCallable, Category = "UI Management")
	void HideAllUI();

	UFUNCTION(BlueprintCallable, Category = "UI Management")
	void UpdateExhibitInfo(const FString& Title, const FString& Description, const FString& Artist, int32 Year);

	UFUNCTION(BlueprintCallable, Category = "UI Management")
	void SetFollowTarget(AVRPawn* Pawn);

	UFUNCTION(BlueprintPure, Category = "UI State")
	bool IsUIVisible(EUIType UIType) const;

	UFUNCTION(BlueprintImplementableEvent, Category = "UI Events")
	void OnUIShown(EUIType UIType);

	UFUNCTION(BlueprintImplementableEvent, Category = "UI Events")
	void OnUIHidden(EUIType UIType);

protected:
	UPROPERTY()
	TMap<EUIType, UWidgetComponent*> ActiveWidgetComponents;

	UPROPERTY()
	TMap<EUIType, UUserWidget*> ActiveWidgets;

	UPROPERTY()
	AVRPawn* FollowTarget;

	UWidgetComponent* CreateWidgetComponent(const FUIWidgetConfig& Config);
	void UpdateWidgetPosition(UWidgetComponent* Widget, const FUIWidgetConfig& Config);
	void UpdateFollowedWidgets();

	UFUNCTION()
	void OnExhibitSelected(AExhibitActor* Exhibit);

	UFUNCTION()
	void OnExhibitDeselected(AExhibitActor* Exhibit);
};
