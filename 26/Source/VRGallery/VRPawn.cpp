#include "VRPawn.h"
#include "Camera/CameraComponent.h"
#include "MotionControllerComponent.h"
#include "EnhancedInputComponent.h"
#include "EnhancedInputSubsystems.h"
#include "InputActionValue.h"
#include "WidgetInteractionComponent.h"
#include "PhysicsEngine/PhysicsHandleComponent.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "NavigationSystem.h"
#include "ExhibitActor.h"
#include "Net/UnrealNetwork.h"

AVRPawn::AVRPawn()
{
	PrimaryActorTick.bCanEverTick = true;
	bReplicates = true;
	SetReplicateMovement(true);

	VROrigin = CreateDefaultSubobject<USceneComponent>(TEXT("VROrigin"));
	VROrigin->SetIsReplicated(true);
	RootComponent = VROrigin;

	Camera = CreateDefaultSubobject<UCameraComponent>(TEXT("Camera"));
	Camera->SetupAttachment(VROrigin);
	Camera->bUsePawnControlRotation = false;
	Camera->SetIsReplicated(true);

	LeftController = CreateDefaultSubobject<UMotionControllerComponent>(TEXT("LeftController"));
	LeftController->SetupAttachment(VROrigin);
	LeftController->MotionSource = FXRMotionControllerBase::LeftHandSourceId;
	LeftController->SetIsReplicated(true);

	RightController = CreateDefaultSubobject<UMotionControllerComponent>(TEXT("RightController"));
	RightController->SetupAttachment(VROrigin);
	RightController->MotionSource = FXRMotionControllerBase::RightHandSourceId;
	RightController->SetIsReplicated(true);

	LeftWidgetInteraction = CreateDefaultSubobject<UWidgetInteractionComponent>(TEXT("LeftWidgetInteraction"));
	LeftWidgetInteraction->SetupAttachment(LeftController);
	LeftWidgetInteraction->InteractionDistance = 300.0f;

	RightWidgetInteraction = CreateDefaultSubobject<UWidgetInteractionComponent>(TEXT("RightWidgetInteraction"));
	RightWidgetInteraction->SetupAttachment(RightController);
	RightWidgetInteraction->InteractionDistance = 300.0f;

	LeftPhysicsHandle = CreateDefaultSubobject<UPhysicsHandleComponent>(TEXT("LeftPhysicsHandle"));
	RightPhysicsHandle = CreateDefaultSubobject<UPhysicsHandleComponent>(TEXT("RightPhysicsHandle"));

	MovementSpeed = 2.0f;
	RotationSpeed = 45.0f;
	TeleportTraceDistance = 1000.0f;
	InteractionTraceChannel = ECC_Visibility;
	InteractionTraceDistance = 100.0f;
	bIgnoreUIInInteractionTrace = true;
	NetworkUpdateInterval = 0.033f;
	LastNetworkUpdateTime = 0.0f;
	PlayerId = 0;

	LeftControllerState = FVRControllerState();
	RightControllerState = FVRControllerState();
	ReplicatedHeadLocation = FVector::ZeroVector;
	ReplicatedHeadRotation = FRotator::ZeroRotator;

	bIsTeleportPreviewing = false;
	LeftGrabbedActor = nullptr;
	RightGrabbedActor = nullptr;
	CurrentInteractingExhibit = nullptr;
}

void AVRPawn::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
	Super::GetLifetimeReplicatedProps(OutLifetimeProps);

	DOREPLIFETIME_CONDITION(AVRPawn, LeftControllerState, COND_SkipOwner);
	DOREPLIFETIME_CONDITION(AVRPawn, RightControllerState, COND_SkipOwner);
	DOREPLIFETIME_CONDITION(AVRPawn, ReplicatedHeadLocation, COND_SkipOwner);
	DOREPLIFETIME_CONDITION(AVRPawn, ReplicatedHeadRotation, COND_SkipOwner);
	DOREPLIFETIME(AVRPawn, PlayerName);
	DOREPLIFETIME(AVRPawn, PlayerId);
	DOREPLIFETIME(AVRPawn, CurrentInteractingExhibit);
}

void AVRPawn::BeginPlay()
{
	Super::BeginPlay();

	if (HasAuthority())
	{
		static int32 NextPlayerId = 1;
		PlayerId = NextPlayerId++;
		PlayerName = FString::Printf(TEXT("Player%d"), PlayerId);
		Multicast_OnPlayerJoined(PlayerName, PlayerId);
	}

	if (IsLocallyControlled())
	{
		if (APlayerController* PlayerController = Cast<APlayerController>(GetController()))
		{
			if (UEnhancedInputLocalPlayerSubsystem* Subsystem = ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(PlayerController->GetLocalPlayer()))
			{
				if (MappingContext)
				{
					Subsystem->AddMappingContext(MappingContext, 0);
				}
			}
		}
	}
}

void AVRPawn::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);

	if (IsLocallyControlled())
	{
		if (LeftPhysicsHandle && LeftGrabbedActor)
		{
			LeftPhysicsHandle->SetTargetLocationAndRotation(
				LeftController->GetComponentLocation(),
				LeftController->GetComponentRotation()
			);
		}

		if (RightPhysicsHandle && RightGrabbedActor)
		{
			RightPhysicsHandle->SetTargetLocationAndRotation(
				RightController->GetComponentLocation(),
				RightController->GetComponentRotation()
			);
		}

		UpdateNetworkState(DeltaTime);
	}
	else
	{
		ApplyRemoteControllerStates();
	}
}

void AVRPawn::UpdateNetworkState(float DeltaTime)
{
	LastNetworkUpdateTime += DeltaTime;

	if (LastNetworkUpdateTime >= NetworkUpdateInterval && HasAuthority())
	{
		LastNetworkUpdateTime = 0.0f;

		if (LeftController)
		{
			LeftControllerState.Location = LeftController->GetComponentLocation();
			LeftControllerState.Rotation = LeftController->GetComponentRotation();
		}

		if (RightController)
		{
			RightControllerState.Location = RightController->GetComponentLocation();
			RightControllerState.Rotation = RightController->GetComponentRotation();
		}

		if (Camera)
		{
			ReplicatedHeadLocation = Camera->GetComponentLocation();
			ReplicatedHeadRotation = Camera->GetComponentRotation();
		}
	}
	else if (LastNetworkUpdateTime >= NetworkUpdateInterval)
	{
		LastNetworkUpdateTime = 0.0f;

		FVRControllerState LocalLeftState;
		FVRControllerState LocalRightState;

		if (LeftController)
		{
			LocalLeftState.Location = LeftController->GetComponentLocation();
			LocalLeftState.Rotation = LeftController->GetComponentRotation();
			LocalLeftState.bIsGrabbing = LeftGrabbedActor != nullptr;
		}

		if (RightController)
		{
			LocalRightState.Location = RightController->GetComponentLocation();
			LocalRightState.Rotation = RightController->GetComponentRotation();
			LocalRightState.bIsGrabbing = RightGrabbedActor != nullptr;
		}

		Server_UpdateControllerStates(LocalLeftState, LocalRightState);

		if (Camera)
		{
			Server_UpdateHeadTransform(Camera->GetComponentLocation(), Camera->GetComponentRotation());
		}
	}
}

void AVRPawn::ApplyRemoteControllerStates()
{
	if (LeftController)
	{
		LeftController->SetWorldLocation(LeftControllerState.Location);
		LeftController->SetWorldRotation(LeftControllerState.Rotation);
	}

	if (RightController)
	{
		RightController->SetWorldLocation(RightControllerState.Location);
		RightController->SetWorldRotation(RightControllerState.Rotation);
	}

	if (Camera)
	{
		Camera->SetWorldLocation(ReplicatedHeadLocation);
		Camera->SetWorldRotation(ReplicatedHeadRotation);
	}
}

void AVRPawn::OnRep_HeadPosition()
{
	if (Camera && !IsLocallyControlled())
	{
		Camera->SetWorldLocation(ReplicatedHeadLocation);
	}
}

void AVRPawn::OnRep_HeadRotation()
{
	if (Camera && !IsLocallyControlled())
	{
		Camera->SetWorldRotation(ReplicatedHeadRotation);
	}
}

void AVRPawn::OnRep_PlayerName()
{
	OnPlayerJoined(PlayerName, PlayerId);
}

void AVRPawn::Server_UpdateControllerStates_Implementation(const FVRControllerState& LeftState, const FVRControllerState& RightState)
{
	LeftControllerState = LeftState;
	RightControllerState = RightState;
}

bool AVRPawn::Server_UpdateControllerStates_Validate(const FVRControllerState& LeftState, const FVRControllerState& RightState)
{
	return true;
}

void AVRPawn::Server_UpdateHeadTransform_Implementation(const FVector& Location, const FRotator& Rotation)
{
	ReplicatedHeadLocation = Location;
	ReplicatedHeadRotation = Rotation;
}

bool AVRPawn::Server_UpdateHeadTransform_Validate(const FVector& Location, const FRotator& Rotation)
{
	return true;
}

void AVRPawn::Server_SetPlayerName_Implementation(const FString& Name)
{
	PlayerName = Name;
}

bool AVRPawn::Server_SetPlayerName_Validate(const FString& Name)
{
	return Name.Len() > 0 && Name.Len() <= 32;
}

void AVRPawn::Multicast_OnPlayerJoined_Implementation(const FString& Name, int32 Id)
{
	OnPlayerJoined(Name, Id);
}

void AVRPawn::SetupPlayerInputComponent(UInputComponent* PlayerInputComponent)
{
	Super::SetupPlayerInputComponent(PlayerInputComponent);

	if (UEnhancedInputComponent* EnhancedInputComponent = CastChecked<UEnhancedInputComponent>(PlayerInputComponent))
	{
		if (MoveAction)
		{
			EnhancedInputComponent->BindAction(MoveAction, ETriggerEvent::Triggered, this, &AVRPawn::Move);
		}

		if (LookAction)
		{
			EnhancedInputComponent->BindAction(LookAction, ETriggerEvent::Triggered, this, &AVRPawn::Look);
		}

		if (GrabAction)
		{
			EnhancedInputComponent->BindAction(GrabAction, ETriggerEvent::Started, this, &AVRPawn::GrabLeft);
			EnhancedInputComponent->BindAction(GrabAction, ETriggerEvent::Completed, this, &AVRPawn::GrabLeft);
		}

		if (TriggerAction)
		{
			EnhancedInputComponent->BindAction(TriggerAction, ETriggerEvent::Started, this, &AVRPawn::TriggerRight);
			EnhancedInputComponent->BindAction(TriggerAction, ETriggerEvent::Completed, this, &AVRPawn::TriggerRight);
		}

		if (TeleportAction)
		{
			EnhancedInputComponent->BindAction(TeleportAction, ETriggerEvent::Started, this, &AVRPawn::StartTeleportPreview);
			EnhancedInputComponent->BindAction(TeleportAction, ETriggerEvent::Completed, this, &AVRPawn::StopTeleportPreview);
		}
	}
}

void AVRPawn::Move(const FInputActionValue& Value)
{
	const FVector2D MovementVector = Value.Get<FVector2D>();

	if (Controller != nullptr && Camera)
	{
		const FRotator YawRotation(0, Camera->GetComponentRotation().Yaw, 0);

		const FVector ForwardDirection = FRotationMatrix(YawRotation).GetUnitAxis(EAxis::X);
		const FVector RightDirection = FRotationMatrix(YawRotation).GetUnitAxis(EAxis::Y);

		AddActorWorldOffset(ForwardDirection * MovementVector.Y * MovementSpeed * GetWorld()->GetDeltaSeconds(), true);
		AddActorWorldOffset(RightDirection * MovementVector.X * MovementSpeed * GetWorld()->GetDeltaSeconds(), true);
	}
}

void AVRPawn::Look(const FInputActionValue& Value)
{
	const FVector2D LookVector = Value.Get<FVector2D>();

	if (Controller != nullptr)
	{
		AddControllerYawInput(LookVector.X * RotationSpeed * GetWorld()->GetDeltaSeconds());
	}
}

void AVRPawn::GrabLeft(const FInputActionValue& Value)
{
	const bool bIsPressed = Value.Get<bool>();

	if (bIsPressed)
	{
		FHitResult HitResult;
		if (TraceForInteractable(HitResult, LeftController))
		{
			if (AExhibitActor* Exhibit = Cast<AExhibitActor>(HitResult.GetActor()))
			{
				Exhibit->OnGrab(this);
				CurrentInteractingExhibit = Exhibit;
			}

			if (UPrimitiveComponent* HitComponent = HitResult.GetComponent())
			{
				HitComponent->SetSimulatePhysics(true);
				LeftPhysicsHandle->GrabComponentAtLocationWithRotation(
					HitComponent,
					NAME_None,
					HitResult.ImpactPoint,
					LeftController->GetComponentRotation()
				);
				LeftGrabbedActor = HitResult.GetActor();
			}
		}
	}
	else
	{
		if (LeftGrabbedActor)
		{
			if (AExhibitActor* Exhibit = Cast<AExhibitActor>(LeftGrabbedActor))
			{
				Exhibit->OnRelease(this);
			}
			LeftPhysicsHandle->ReleaseComponent();
			LeftGrabbedActor = nullptr;
		}
	}
}

void AVRPawn::GrabRight(const FInputActionValue& Value)
{
	const bool bIsPressed = Value.Get<bool>();

	if (bIsPressed)
	{
		FHitResult HitResult;
		if (TraceForInteractable(HitResult, RightController))
		{
			if (AExhibitActor* Exhibit = Cast<AExhibitActor>(HitResult.GetActor()))
			{
				Exhibit->OnGrab(this);
				CurrentInteractingExhibit = Exhibit;
			}

			if (UPrimitiveComponent* HitComponent = HitResult.GetComponent())
			{
				HitComponent->SetSimulatePhysics(true);
				RightPhysicsHandle->GrabComponentAtLocationWithRotation(
					HitComponent,
					NAME_None,
					HitResult.ImpactPoint,
					RightController->GetComponentRotation()
				);
				RightGrabbedActor = HitResult.GetActor();
			}
		}
	}
	else
	{
		if (RightGrabbedActor)
		{
			if (AExhibitActor* Exhibit = Cast<AExhibitActor>(RightGrabbedActor))
			{
				Exhibit->OnRelease(this);
			}
			RightPhysicsHandle->ReleaseComponent();
			RightGrabbedActor = nullptr;
		}
	}
}

void AVRPawn::TriggerLeft(const FInputActionValue& Value)
{
	const bool bIsPressed = Value.Get<bool>();

	if (bIsPressed)
	{
		LeftWidgetInteraction->PressPointerKey(EKeys::LeftMouseButton);
	}
	else
	{
		LeftWidgetInteraction->ReleasePointerKey(EKeys::LeftMouseButton);
	}
}

void AVRPawn::TriggerRight(const FInputActionValue& Value)
{
	const bool bIsPressed = Value.Get<bool>();

	if (bIsPressed)
	{
		RightWidgetInteraction->PressPointerKey(EKeys::LeftMouseButton);

		FHitResult HitResult;
		if (TraceForInteractable(HitResult, RightController))
		{
			if (AExhibitActor* Exhibit = Cast<AExhibitActor>(HitResult.GetActor()))
			{
				Exhibit->OnSelect(this);
				CurrentInteractingExhibit = Exhibit;
			}
		}
	}
	else
	{
		RightWidgetInteraction->ReleasePointerKey(EKeys::LeftMouseButton);
	}
}

void AVRPawn::StartTeleportPreview(const FInputActionValue& Value)
{
	bIsTeleportPreviewing = true;
}

void AVRPawn::StopTeleportPreview(const FInputActionValue& Value)
{
	if (bIsTeleportPreviewing)
	{
		PerformTeleport(Value);
	}
	bIsTeleportPreviewing = false;
}

void AVRPawn::PerformTeleport(const FInputActionValue& Value)
{
	FHitResult HitResult;
	const FVector Start = RightController->GetComponentLocation();
	const FVector End = Start + (RightController->GetForwardVector() * TeleportTraceDistance);

	FCollisionQueryParams Params;
	Params.AddIgnoredActor(this);

	if (GetWorld()->LineTraceSingleByChannel(HitResult, Start, End, ECC_Visibility, Params))
	{
		if (UNavigationSystemV1* NavSys = UNavigationSystemV1::GetCurrent(GetWorld()))
		{
			FNavLocation NavLocation;
			if (NavSys->ProjectPointToNavigation(HitResult.Location, NavLocation))
			{
				TeleportTo(NavLocation.Location, GetActorRotation());
			}
		}
	}
}

bool AVRPawn::TraceForInteractable(FHitResult& OutHit, UMotionControllerComponent* Controller)
{
	if (!Controller) return false;

	const FVector Start = Controller->GetComponentLocation();
	const FVector End = Start + (Controller->GetForwardVector() * InteractionTraceDistance);

	FCollisionQueryParams Params;
	Params.AddIgnoredActor(this);

	TArray<FHitResult> HitResults;
	bool bHit = GetWorld()->LineTraceMultiByChannel(HitResults, Start, End, InteractionTraceChannel, Params);

	if (bHit)
	{
		for (const FHitResult& Hit : HitResults)
		{
			if (bIgnoreUIInInteractionTrace && Hit.Component.IsValid())
			{
				if (IsUIComponent(Hit.Component.Get()))
				{
					continue;
				}
			}
			OutHit = Hit;
			return true;
		}
	}

	return false;
}

bool AVRPawn::IsUIComponent(UPrimitiveComponent* Component) const
{
	if (!Component) return false;

	if (Component->GetName().Contains(TEXT("WidgetComponent")))
	{
		return true;
	}

	if (Component->GetCollisionProfileName() == FName(TEXT("UI")))
	{
		return true;
	}

	AActor* Owner = Component->GetOwner();
	if (Owner)
	{
		TArray<UWidgetInteractionComponent*> WidgetInteractions;
		Owner->GetComponents<UWidgetInteractionComponent>(WidgetInteractions);
		if (WidgetInteractions.Num() > 0)
		{
			return true;
		}
	}

	return false;
}
