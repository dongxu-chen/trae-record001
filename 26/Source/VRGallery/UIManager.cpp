#include "UIManager.h"
#include "Components/WidgetComponent.h"
#include "Blueprint/UserWidget.h"
#include "VRPawn.h"
#include "ExhibitActor.h"
#include "Kismet/GameplayStatics.h"

AUIManager::AUIManager()
{
	PrimaryActorTick.bCanEverTick = true;

	bAutoShowMainMenuOnStart = false;
	UIFadeDuration = 0.3f;
	CurrentVisibleUIType = EUIType::MainMenu;
	bAnyUIVisible = false;
	FollowTarget = nullptr;
}

void AUIManager::BeginPlay()
{
	Super::BeginPlay();

	if (bAutoShowMainMenuOnStart)
	{
		ShowUI(EUIType::MainMenu);
	}

	if (APlayerController* PlayerController = UGameplayStatics::GetPlayerController(GetWorld(), 0))
	{
		if (APawn* Pawn = PlayerController->GetPawn())
		{
			if (AVRPawn* VRPawn = Cast<AVRPawn>(Pawn))
			{
				SetFollowTarget(VRPawn);
			}
		}
	}
}

void AUIManager::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);

	UpdateFollowedWidgets();
}

void AUIManager::ShowUI(EUIType UIType)
{
	if (FUIWidgetConfig* Config = UIConfigurations.Find(UIType))
	{
		UWidgetComponent* ExistingWidget = nullptr;
		if (UWidgetComponent** FoundWidget = ActiveWidgetComponents.Find(UIType))
		{
			ExistingWidget = *FoundWidget;
		}

		if (!ExistingWidget)
		{
			ExistingWidget = CreateWidgetComponent(*Config);
			ActiveWidgetComponents.Add(UIType, ExistingWidget);
		}

		if (ExistingWidget)
		{
			ExistingWidget->SetVisibility(true);
			UpdateWidgetPosition(ExistingWidget, *Config);
			CurrentVisibleUIType = UIType;
			bAnyUIVisible = true;
			OnUIShown(UIType);
		}
	}
}

void AUIManager::HideUI(EUIType UIType)
{
	if (UWidgetComponent** FoundWidget = ActiveWidgetComponents.Find(UIType))
	{
		if (UWidgetComponent* Widget = *FoundWidget)
		{
			Widget->SetVisibility(false);
		}
	}

	bAnyUIVisible = false;
	for (const auto& Pair : ActiveWidgetComponents)
	{
		if (UWidgetComponent* Widget = Pair.Value)
		{
			if (Widget->IsVisible())
			{
				bAnyUIVisible = true;
				break;
			}
		}
	}

	OnUIHidden(UIType);
}

void AUIManager::ToggleUI(EUIType UIType)
{
	if (IsUIVisible(UIType))
	{
		HideUI(UIType);
	}
	else
	{
		ShowUI(UIType);
	}
}

void AUIManager::HideAllUI()
{
	for (const auto& Pair : ActiveWidgetComponents)
	{
		if (UWidgetComponent* Widget = Pair.Value)
		{
			Widget->SetVisibility(false);
		}
		OnUIHidden(Pair.Key);
	}

	bAnyUIVisible = false;
}

void AUIManager::UpdateExhibitInfo(const FString& Title, const FString& Description, const FString& Artist, int32 Year)
{
	if (UUserWidget** FoundWidget = ActiveWidgets.Find(EUIType::ExhibitInfo))
	{
		if (UUserWidget* Widget = *FoundWidget)
		{
		}
	}
}

void AUIManager::SetFollowTarget(AVRPawn* Pawn)
{
	FollowTarget = Pawn;
}

bool AUIManager::IsUIVisible(EUIType UIType) const
{
	if (const UWidgetComponent* const* FoundWidget = ActiveWidgetComponents.Find(UIType))
	{
		if (const UWidgetComponent* Widget = *FoundWidget)
		{
			return Widget->IsVisible();
		}
	}
	return false;
}

UWidgetComponent* AUIManager::CreateWidgetComponent(const FUIWidgetConfig& Config)
{
	UWidgetComponent* WidgetComponent = NewObject<UWidgetComponent>(this);
	WidgetComponent->RegisterComponent();
	WidgetComponent->SetWorldLocation(GetActorLocation() + Config.Location);
	WidgetComponent->SetWorldRotation(Config.Rotation);
	WidgetComponent->SetDrawSize(Config.DrawSize);
	WidgetComponent->SetWidgetSpace(EWidgetSpace::World);

	if (Config.WidgetClass)
	{
		UUserWidget* Widget = CreateWidget<UUserWidget>(GetWorld(), Config.WidgetClass);
		WidgetComponent->SetWidget(Widget);
	}

	return WidgetComponent;
}

void AUIManager::UpdateWidgetPosition(UWidgetComponent* Widget, const FUIWidgetConfig& Config)
{
	if (!Widget) return;

	if (Config.bFollowPlayer && FollowTarget)
	{
		FVector CameraLocation = FollowTarget->Camera->GetComponentLocation();
		FVector CameraForward = FollowTarget->Camera->GetForwardVector();
		CameraForward.Z = 0.0f;
		CameraForward.Normalize();

		FVector TargetLocation = CameraLocation + CameraForward * Config.FollowDistance + Config.Location;
		Widget->SetWorldLocation(TargetLocation);

		FRotator LookAtRotation = UKismetMathLibrary::FindLookAtRotation(
			Widget->GetComponentLocation(),
			CameraLocation
		);
		Widget->SetWorldRotation(LookAtRotation);
	}
	else
	{
		Widget->SetWorldLocation(GetActorLocation() + Config.Location);
		Widget->SetWorldRotation(Config.Rotation);
	}
}

void AUIManager::UpdateFollowedWidgets()
{
	for (const auto& Pair : UIConfigurations)
	{
		if (Pair.Value.bFollowPlayer)
		{
			if (UWidgetComponent** FoundWidget = ActiveWidgetComponents.Find(Pair.Key))
			{
				if (UWidgetComponent* Widget = *FoundWidget)
				{
					if (Widget->IsVisible())
					{
						UpdateWidgetPosition(Widget, Pair.Value);
					}
				}
			}
		}
	}
}

void AUIManager::OnExhibitSelected(AExhibitActor* Exhibit)
{
	if (Exhibit)
	{
		UpdateExhibitInfo(
			Exhibit->ExhibitTitle,
			Exhibit->ExhibitDescription,
			Exhibit->ExhibitArtist,
			Exhibit->ExhibitYear
		);
		ShowUI(EUIType::ExhibitInfo);
	}
}

void AUIManager::OnExhibitDeselected(AExhibitActor* Exhibit)
{
	HideUI(EUIType::ExhibitInfo);
}
