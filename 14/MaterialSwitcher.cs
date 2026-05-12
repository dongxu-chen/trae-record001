using System.Collections.Generic;
using UnityEngine;

public class MaterialSwitcher : MonoBehaviour
{
    [Header("Target Objects")]
    public List<GameObject> targetObjects;
    
    [Header("Materials")]
    public List<Material> materials;
    
    [Header("Settings")]
    public int currentMaterialIndex = 0;
    public bool applyToChildren = true;
    
    [Header("Shadow Settings")]
    public bool updateShadows = true;
    public bool updateGI = true;
    public ShadowCastingMode shadowCastingMode = ShadowCastingMode.On;
    public bool receiveShadows = true;
    
    private Dictionary<Renderer, Material[]> originalMaterials = new Dictionary<Renderer, Material[]>();
    private List<Renderer> affectedRenderers = new List<Renderer>();
    
    void Start()
    {
        if (targetObjects == null || targetObjects.Count == 0)
        {
            targetObjects = new List<GameObject> { gameObject };
        }
        
        StoreOriginalMaterials();
        CollectAffectedRenderers();
    }
    
    void StoreOriginalMaterials()
    {
        originalMaterials.Clear();
        
        foreach (GameObject obj in targetObjects)
        {
            if (obj == null)
                continue;
            
            if (applyToChildren)
            {
                Renderer[] renderers = obj.GetComponentsInChildren<Renderer>(true);
                foreach (Renderer renderer in renderers)
                {
                    if (!originalMaterials.ContainsKey(renderer))
                    {
                        originalMaterials[renderer] = renderer.materials;
                    }
                }
            }
            else
            {
                Renderer renderer = obj.GetComponent<Renderer>();
                if (renderer != null && !originalMaterials.ContainsKey(renderer))
                {
                    originalMaterials[renderer] = renderer.materials;
                }
            }
        }
    }
    
    void CollectAffectedRenderers()
    {
        affectedRenderers.Clear();
        
        foreach (GameObject obj in targetObjects)
        {
            if (obj == null)
                continue;
            
            if (applyToChildren)
            {
                Renderer[] renderers = obj.GetComponentsInChildren<Renderer>(true);
                foreach (Renderer renderer in renderers)
                {
                    if (!affectedRenderers.Contains(renderer))
                    {
                        affectedRenderers.Add(renderer);
                    }
                }
            }
            else
            {
                Renderer renderer = obj.GetComponent<Renderer>();
                if (renderer != null && !affectedRenderers.Contains(renderer))
                {
                    affectedRenderers.Add(renderer);
                }
            }
        }
    }
    
    public void SwitchToNextMaterial()
    {
        if (materials == null || materials.Count == 0)
            return;
        
        currentMaterialIndex = (currentMaterialIndex + 1) % materials.Count;
        ApplyMaterial(materials[currentMaterialIndex]);
    }
    
    public void SwitchToPreviousMaterial()
    {
        if (materials == null || materials.Count == 0)
            return;
        
        currentMaterialIndex = (currentMaterialIndex - 1 + materials.Count) % materials.Count;
        ApplyMaterial(materials[currentMaterialIndex]);
    }
    
    public void SwitchToMaterial(int index)
    {
        if (materials == null || materials.Count == 0)
            return;
        
        if (index < 0 || index >= materials.Count)
        {
            Debug.LogWarning("Material index out of range: " + index);
            return;
        }
        
        currentMaterialIndex = index;
        ApplyMaterial(materials[currentMaterialIndex]);
    }
    
    public void SwitchToMaterial(Material material)
    {
        if (materials == null || materials.Count == 0)
            return;
        
        int index = materials.IndexOf(material);
        if (index == -1)
        {
            Debug.LogWarning("Material not found in list: " + material.name);
            return;
        }
        
        currentMaterialIndex = index;
        ApplyMaterial(material);
    }
    
    public void ResetToOriginalMaterial()
    {
        foreach (var kvp in originalMaterials)
        {
            if (kvp.Key != null)
            {
                kvp.Key.materials = kvp.Value;
                
                if (updateShadows)
                {
                    UpdateRendererShadowSettings(kvp.Key);
                }
                
                if (updateGI)
                {
                    UpdateGIMaterials(kvp.Key);
                }
            }
        }
        
        currentMaterialIndex = 0;
        UpdateAllRenderers();
    }
    
    void ApplyMaterial(Material material)
    {
        if (affectedRenderers.Count == 0)
        {
            CollectAffectedRenderers();
        }
        
        foreach (Renderer renderer in affectedRenderers)
        {
            if (renderer == null)
                continue;
            
            ApplyMaterialToRenderer(renderer, material);
        }
        
        UpdateAllRenderers();
    }
    
    void ApplyMaterialToRenderer(Renderer renderer, Material material)
    {
        if (renderer == null || material == null)
            return;
        
        Material[] newMaterials = new Material[renderer.materials.Length];
        for (int i = 0; i < newMaterials.Length; i++)
        {
            newMaterials[i] = material;
        }
        renderer.materials = newMaterials;
        
        if (updateShadows)
        {
            UpdateRendererShadowSettings(renderer);
        }
        
        if (updateGI)
        {
            UpdateGIMaterials(renderer);
        }
    }
    
    void UpdateRendererShadowSettings(Renderer renderer)
    {
        if (renderer == null)
            return;
        
        renderer.shadowCastingMode = shadowCastingMode;
        renderer.receiveShadows = receiveShadows;
        
        MeshRenderer meshRenderer = renderer as MeshRenderer;
        if (meshRenderer != null)
        {
            meshRenderer.allowOcclusionWhenDynamic = true;
        }
    }
    
    void UpdateGIMaterials(Renderer renderer)
    {
        if (renderer == null)
            return;
        
        renderer.UpdateGIMaterials();
    }
    
    void UpdateAllRenderers()
    {
        if (!updateGI || affectedRenderers.Count == 0)
            return;
        
        DynamicGI.UpdateEnvironment();
        
        foreach (Renderer renderer in affectedRenderers)
        {
            if (renderer != null)
            {
                renderer.enabled = false;
                renderer.enabled = true;
            }
        }
    }
    
    public int GetMaterialCount()
    {
        return materials != null ? materials.Count : 0;
    }
    
    public Material GetCurrentMaterial()
    {
        if (materials != null && currentMaterialIndex >= 0 && currentMaterialIndex < materials.Count)
        {
            return materials[currentMaterialIndex];
        }
        return null;
    }
    
    public string GetCurrentMaterialName()
    {
        Material current = GetCurrentMaterial();
        return current != null ? current.name : "None";
    }
    
    public void RefreshRenderers()
    {
        CollectAffectedRenderers();
        StoreOriginalMaterials();
    }
}
