#include "TeleportVolume.h"
#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/TextRenderComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Sound/SoundBase.h"
#include "NiagaraSystem.h"
#include "NiagaraFunctionLibrary.h"
#include "Kismet/GameplayStatics.h"
#include "GameFramework/Pawn.h"
#include "TimerManager.h"

ATeleportVolume::ATeleportVolume()
{
	PrimaryActorTick.bCanEverTick = true;

	TriggerVolume = CreateDefaultSubobject<UBoxComponent>(TEXT("TriggerVolume"));
	RootComponent = TriggerVolume;
	TriggerVolume->SetCollisionProfileName(TEXT("OverlapAllDynamic"));
	TriggerVolume->SetBoxExtent(FVector(200.0f, 200.0f, 50.0f));

	VisualMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("VisualMesh"));
	VisualMesh->SetupAttachment(TriggerVolume);
	VisualMesh->SetCollisionProfileName(TEXT("NoCollision"));

	DestinationLabel = CreateDefaultSubobject<UTextRenderComponent>(TEXT("DestinationLabel"));
	DestinationLabel->SetupAttachment(TriggerVolume);
	DestinationLabel->SetRelativeLocation(FVector(0.0f, 0.0f, 100.0f));
	DestinationLabel->SetRelativeRotation(FRotator(90.0f, 0.0f, 0.0f));
	DestinationLabel->HorizontalAlignment = EHTA_Center;
	DestinationLabel->SetText(FText::FromString(TEXT("Teleport")));

	DestinationTag = NAME_None;
	TeleportOffset = FVector(0.0f, 0.0f, 10.0f);
	TeleportType = ETeleportType::Instant;
	FadeDuration = 0.5f;
	bRotateToDestination = false;
	TargetRotation = FRotator::ZeroRotator;

	ActiveColor = FLinearColor(0.0f, 1.0f, 0.0f, 1.0f);
	InactiveColor = FLinearColor(0.5f, 0.5f, 0.5f, 1.0f);
	PulseSpeed = 1.0f;

	bIsActive = true;
	bIsPlayerInside = false;
	CurrentPlayer = nullptr;
	TeleportCooldown = 2.0f;
	bIsOnCooldown = false;
	CooldownRemaining = 0.0f;
	LastTeleportTime = 0.0f;
	LastTeleportDestination = FVector::ZeroVector;
	PulseTime = 0.0f;
}

void ATeleportVolume::BeginPlay()
{
	Super::BeginPlay();

	if (TriggerVolume)
	{
		TriggerVolume->OnComponentBeginOverlap.AddDynamic(this, &ATeleportVolume::OnVolumeBeginOverlap);
		TriggerVolume->OnComponentEndOverlap.AddDynamic(this, &ATeleportVolume::OnVolumeEndOverlap);
	}

	if (VisualMesh)
	{
		UMaterialInstanceDynamic* MID = VisualMesh->CreateAndSetMaterialInstanceDynamic(0);
		if (MID)
		{
			MID->SetVectorParameterValue(TEXT("BaseColor"), bIsActive ? ActiveColor : InactiveColor);
		}
	}
}

void ATeleportVolume::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);

	if (bIsActive && VisualMesh)
	{
		PulseTime += DeltaTime * PulseSpeed;
		float PulseAlpha = (FMath::Sin(PulseTime) + 1.0f) / 2.0f;

		if (UMaterialInstanceDynamic* MID = Cast<UMaterialInstanceDynamic>(VisualMesh->GetMaterial(0)))
		{
			FLinearColor CurrentColor = FLinearColor::LerpUsingHSV(InactiveColor, ActiveColor, PulseAlpha);
			MID->SetVectorParameterValue(TEXT("BaseColor"), CurrentColor);
		}
	}

	if (bIsOnCooldown)
	{
		CooldownRemaining -= DeltaTime;
		if (CooldownRemaining <= 0.0f)
		{
			OnCooldownComplete();
		}
	}
}

void ATeleportVolume::ActivateVolume()
{
	bIsActive = true;

	if (VisualMesh)
	{
		if (UMaterialInstanceDynamic* MID = Cast<UMaterialInstanceDynamic>(VisualMesh->GetMaterial(0)))
		{
			MID->SetVectorParameterValue(TEXT("BaseColor"), ActiveColor);
		}
	}
}

void ATeleportVolume::DeactivateVolume()
{
	bIsActive = false;
	bIsPlayerInside = false;
	CurrentPlayer = nullptr;

	if (VisualMesh)
	{
		if (UMaterialInstanceDynamic* MID = Cast<UMaterialInstanceDynamic>(VisualMesh->GetMaterial(0)))
		{
			MID->SetVectorParameterValue(TEXT("BaseColor"), InactiveColor);
		}
	}
}

void ATeleportVolume::TeleportPlayer(APawn* PlayerPawn)
{
	if (!PlayerPawn || !bIsActive) return;

	if (!CanTeleport())
	{
		return;
	}

	OnTeleportStarted(PlayerPawn);

	if (TeleportSound)
	{
		UGameplayStatics::PlaySoundAtLocation(this, TeleportSound, GetActorLocation());
	}

	if (TeleportVFX)
	{
		UNiagaraFunctionLibrary::SpawnSystemAtLocation(this, TeleportVFX, GetActorLocation());
	}

	switch (TeleportType)
	{
	case ETeleportType::Instant:
		PerformInstantTeleport(PlayerPawn);
		break;
	case ETeleportType::Fade:
		PerformFadeTeleport(PlayerPawn);
		break;
	case ETeleportType::Arc:
		PerformInstantTeleport(PlayerPawn);
		break;
	default:
		PerformInstantTeleport(PlayerPawn);
		break;
	}

	StartCooldown();
}

void ATeleportVolume::OnVolumeBeginOverlap(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor, UPrimitiveComponent* OtherComp, int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult)
{
	if (APawn* Pawn = Cast<APawn>(OtherActor))
	{
		if (Pawn->IsLocallyControlled() || Pawn->IsPlayerControlled())
		{
			bIsPlayerInside = true;
			CurrentPlayer = Pawn;
			TeleportPlayer(Pawn);
		}
	}
}

void ATeleportVolume::OnVolumeEndOverlap(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor, UPrimitiveComponent* OtherComp, int32 OtherBodyIndex)
{
	if (APawn* Pawn = Cast<APawn>(OtherActor))
	{
		if (Pawn == CurrentPlayer)
		{
			bIsPlayerInside = false;
			CurrentPlayer = nullptr;
		}
	}
}

FVector ATeleportVolume::FindDestinationLocation() const
{
	if (DestinationTag == NAME_None)
	{
		return GetActorLocation() + FVector(500.0f, 0.0f, 0.0f);
	}

	TArray<AActor*> FoundActors;
	UGameplayStatics::GetAllActorsWithTag(GetWorld(), DestinationTag, FoundActors);

	if (FoundActors.Num() > 0)
	{
		return FoundActors[0]->GetActorLocation() + TeleportOffset;
	}

	return GetActorLocation() + FVector(500.0f, 0.0f, 0.0f);
}

void ATeleportVolume::PerformInstantTeleport(APawn* PlayerPawn)
{
	FVector Destination = FindDestinationLocation();

	float DistanceToDestination = FVector::Dist(PlayerPawn->GetActorLocation(), Destination);
	float DistanceToLastDestination = FVector::Dist(LastTeleportDestination, FVector::ZeroVector) > 0.0f
		? FVector::Dist(PlayerPawn->GetActorLocation(), LastTeleportDestination)
		: FLT_MAX;

	if (DistanceToDestination < 10.0f && DistanceToLastDestination < 10.0f)
	{
		return;
	}

	LastTeleportDestination = Destination;

	FRotator NewRotation = bRotateToDestination ? TargetRotation : PlayerPawn->GetActorRotation();

	PlayerPawn->TeleportTo(Destination, NewRotation, false, true);

	OnTeleportCompleted(PlayerPawn);
}

void ATeleportVolume::PerformFadeTeleport(APawn* PlayerPawn)
{
	PerformInstantTeleport(PlayerPawn);
}

void ATeleportVolume::StartCooldown()
{
	bIsOnCooldown = true;
	CooldownRemaining = TeleportCooldown;
	LastTeleportTime = GetWorld()->GetTimeSeconds();
}

void ATeleportVolume::OnCooldownComplete()
{
	bIsOnCooldown = false;
	CooldownRemaining = 0.0f;

	bIsPlayerInside = false;
	CurrentPlayer = nullptr;
}

bool ATeleportVolume::CanTeleport() const
{
	if (bIsOnCooldown)
	{
		return false;
	}

	float CurrentTime = GetWorld()->GetTimeSeconds();
	if (CurrentTime - LastTeleportTime < TeleportCooldown)
	{
		return false;
	}

	return true;
}
