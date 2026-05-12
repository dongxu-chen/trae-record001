using UnrealBuildTool;
using System.Collections.Generic;

public class VRGalleryEditorTarget : TargetRules
{
	public VRGalleryEditorTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Editor;
		DefaultBuildSettings = BuildSettingsVersion.V2;
		ExtraModuleNames.AddRange( new string[] { "VRGallery" } );
	}
}
