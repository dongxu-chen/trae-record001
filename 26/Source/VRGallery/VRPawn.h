#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Pawn.h"
#include "Net/UnrealNetwork.h"
#include "VRPawn.generated.h"

class UCameraComponent;
class UMotionControllerComponent;
class UInputMappingContext;
class UInputAction;
struct FInputActionValue;
class UWidgetInteractionComponent;

USTRUCT(BlueprintType)
struct FVRControllerState
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly)
	FVector Location;

	UPROPERTY(BlueprintReadOnly)
	FRotator Rotation;

	UPROPERTY(BlueprintReadOnly)
	bool bIsGrabbing;

	UPROPERTY(BlueprintReadOnly)
	bool bIsPressed;
};

UCLASS()
class VRGALLERY_API AVRPawn : public APawn
{
	GENERATED_BODY()

public:
	AVRPawn();

	virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;

protected:
	virtual void BeginPlay() override;
	virtual void SetupPlayerInputComponent(class UInputComponent* PlayerInputComponent) override;

public:
	virtual void Tick(float DeltaTime) override;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "VR Components")
	USceneComponent* VROrigin;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "VR Components")
	UCameraComponent* Camera;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "VR Components")
	UMotionControllerComponent* LeftController;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "VR Components")
	UMotionControllerComponent* RightController;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "VR Components")
	UWidgetInteractionComponent* LeftWidgetInteraction;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "VR Components")
	UWidgetInteractionComponent* RightWidgetInteraction;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Replicated, Category = "VR Network")
	FVRControllerState LeftControllerState;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Replicated, Category = "VR Network")
	FVRControllerState RightControllerState;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, ReplicatedUsing = OnRep_HeadPosition, Category = "VR Network")
	FVector ReplicatedHeadLocation;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, ReplicatedUsing = OnRep_HeadRotation, Category = "VR Network")
	FRotator ReplicatedHeadRotation;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, ReplicatedUsing = OnRep_PlayerName, Category = "VR Network")
	FString PlayerName;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Replicated, Category = "VR Network")
	int32 PlayerId;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "VR Movement")
	float MovementSpeed;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "VR Movement")
	float RotationSpeed;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "VR Movement")
	float TeleportTraceDistance;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Input")
	UInputMappingContext* MappingContext;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Input")
	UInputAction* MoveAction;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Input")
	UInputAction* LookAction;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Input")
	UInputAction* GrabAction;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Input")
	UInputAction* TriggerAction;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Input")
	UInputAction* TeleportAction;

	UPROPERTY(VisibleAnywhere, BlueprintReadWrite, Category = "VR Interaction")
	class AExhibitActor* CurrentInteractingExhibit;

protected:
	void Move(const FInputActionValue& Value);
	void Look(const FInputActionValue& Value);
	void GrabLeft(const FInputActionValue& Value);
	void GrabRight(const FInputActionValue& Value);
	void TriggerLeft(const FInputActionValue& Value);
	void TriggerRight(const FInputActionValue& Value);
	void StartTeleportPreview(const FInputActionValue& Value);
	void StopTeleportPreview(const FInputActionValue& Value);
	void PerformTeleport(const FInputActionValue& Value);

	bool bIsTeleportPreviewing;
	FVector TeleportDestination;

	UPROPERTY()
	class AActor* LeftGrabbedActor;

	UPROPERTY()
	class AActor* RightGrabbedActor;

	UPROPERTY()
	class UPhysicsHandleComponent* LeftPhysicsHandle;

	UPROPERTY()
	class UPhysicsHandleComponent* RightPhysicsHandle;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "VR Interaction")
	TEnumAsByte<ECollisionChannel> InteractionTraceChannel;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "VR Interaction")
	float InteractionTraceDistance;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "VR Interaction")
	bool bIgnoreUIInInteractionTrace;

	bool TraceForInteractable(FHitResult& OutHit, UMotionControllerComponent* Controller);
	bool IsUIComponent(UPrimitiveComponent* Component) const;

protected:
	UFUNCTION()
	void OnRep_HeadPosition();

	UFUNCTION()
	void OnRep_HeadRotation();

	UFUNCTION()
	void OnRep_PlayerName();

	UFUNCTION(Server, Reliable, WithValidation)
	void Server_UpdateControllerStates(const FVRControllerState& LeftState, const FVRControllerState& RightState);
	void Server_UpdateControllerStates_Implementation(const FVRControllerState& LeftState, const FVRControllerState& RightState);
	bool Server_UpdateControllerStates_Validate(const FVRControllerState& LeftState, const FVRControllerState& RightState);

	UFUNCTION(Server, Reliable, WithValidation)
	void Server_UpdateHeadTransform(const FVector& Location, const FRotator& Rotation);
	void Server_UpdateHeadTransform_Implementation(const FVector& Location, const FRotator& Rotation);
	bool Server_UpdateHeadTransform_Validate(const FVector& Location, const FRotator& Rotation);

	UFUNCTION(Server, Reliable, WithValidation)
	void Server_SetPlayerName(const FString& Name);
	void Server_SetPlayerName_Implementation(const FString& Name);
	bool Server_SetPlayerName_Validate(const FString& Name);

	UFUNCTION(NetMulticast, Reliable)
	void Multicast_OnPlayerJoined(const FString& Name, int32 Id);
	void Multicast_OnPlayerJoined_Implementation(const FString& Name, int32 Id);

	UFUNCTION(BlueprintImplementableEvent, Category = "VR Network")
	void OnPlayerJoined(const FString& Name, int32 Id);

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "VR Network")
	float NetworkUpdateInterval;

	float LastNetworkUpdateTime;

	void UpdateNetworkState(float DeltaTime);
	void ApplyRemoteControllerStates();
};
