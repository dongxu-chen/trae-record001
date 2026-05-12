#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "TeleportVolume.generated.h"

class UBoxComponent;
class UStaticMeshComponent;
class UTextRenderComponent;
class UNiagaraSystem;
class UNiagaraComponent;

UENUM(BlueprintType)
enum class ETeleportType : uint8
{
	Instant,
	Fade,
	Arc
};

UCLASS()
class VRGALLERY_API ATeleportVolume : public AActor
{
	GENERATED_BODY()

public:
	ATeleportVolume();

protected:
	virtual void BeginPlay() override;

public:
	virtual void Tick(float DeltaTime) override;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Teleport")
	UBoxComponent* TriggerVolume;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Teleport")
	UStaticMeshComponent* VisualMesh;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Teleport")
	UTextRenderComponent* DestinationLabel;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Teleport Settings")
	FName DestinationTag;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Teleport Settings")
	FVector TeleportOffset;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Teleport Settings")
	ETeleportType TeleportType;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Teleport Settings")
	float FadeDuration;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Teleport Settings")
	bool bRotateToDestination;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Teleport Settings")
	FRotator TargetRotation;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Visuals")
	FLinearColor ActiveColor;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Visuals")
	FLinearColor InactiveColor;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Visuals")
	float PulseSpeed;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Audio")
	class USoundBase* TeleportSound;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Effects")
	UNiagaraSystem* TeleportVFX;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "State")
	bool bIsActive;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "State")
	bool bIsPlayerInside;

	UFUNCTION(BlueprintCallable, Category = "Teleport")
	void ActivateVolume();

	UFUNCTION(BlueprintCallable, Category = "Teleport")
	void DeactivateVolume();

	UFUNCTION(BlueprintCallable, Category = "Teleport")
	void TeleportPlayer(APawn* PlayerPawn);

	UFUNCTION(BlueprintImplementableEvent, Category = "Teleport Events")
	void OnTeleportStarted(APawn* PlayerPawn);

	UFUNCTION(BlueprintImplementableEvent, Category = "Teleport Events")
	void OnTeleportCompleted(APawn* PlayerPawn);

protected:
	UFUNCTION()
	void OnVolumeBeginOverlap(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor, UPrimitiveComponent* OtherComp, int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult);

	UFUNCTION()
	void OnVolumeEndOverlap(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor, UPrimitiveComponent* OtherComp, int32 OtherBodyIndex);

	FVector FindDestinationLocation() const;
	void PerformInstantTeleport(APawn* PlayerPawn);
	void PerformFadeTeleport(APawn* PlayerPawn);

	UPROPERTY()
	class APawn* CurrentPlayer;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Teleport Settings")
	float TeleportCooldown;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "State")
	bool bIsOnCooldown;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "State")
	float CooldownRemaining;

	float PulseTime;
	float LastTeleportTime;
	FVector LastTeleportDestination;
	FTimerHandle CooldownTimerHandle;

	void StartCooldown();
	void OnCooldownComplete();
	bool CanTeleport() const;
};
