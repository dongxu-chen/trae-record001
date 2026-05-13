using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Events;

public enum DoorState
{
    Closed,
    Opening,
    Open,
    Closing
}

public class DoorInteract : MonoBehaviour
{
    [Header("Door Settings")]
    public Transform doorTransform;
    public string doorName = "Door";
    public float interactDistance = 3.0f;
    public KeyCode interactKey = KeyCode.E;
    public bool useMouseClick = true;
    public int mouseButton = 0;
    
    [Header("Animation Settings")]
    public float openAngle = 90.0f;
    public float animationDuration = 0.5f;
    public AnimationCurve animationCurve = AnimationCurve.EaseInOut(0.0f, 0.0f, 1.0f, 1.0f);
    public Vector3 rotationAxis = Vector3.up;
    public bool autoClose = false;
    public float autoCloseDelay = 3.0f;
    
    [Header("Audio Settings")]
    public AudioClip openSound;
    public AudioClip closeSound;
    public AudioSource audioSource;
    
    [Header("Events")]
    public UnityEvent OnDoorOpen;
    public UnityEvent OnDoorClose;
    
    [Header("UI")]
    public bool showPrompt = true;
    public string promptText = "按 E 开门";
    public float promptDistance = 2.5f;
    
    private DoorState currentState = DoorState.Closed;
    private Quaternion closedRotation;
    private Quaternion openRotation;
    private float animationProgress = 0.0f;
    private bool isAnimating = false;
    private float autoCloseTimer = 0.0f;
    private bool isInRange = false;
    private static List<DoorInteract> allDoors = new List<DoorInteract>();
    
    void Awake()
    {
        if (doorTransform == null)
        {
            doorTransform = transform;
        }
        
        closedRotation = doorTransform.localRotation;
        openRotation = closedRotation * Quaternion.AngleAxis(openAngle, rotationAxis);
        
        if (!allDoors.Contains(this))
        {
            allDoors.Add(this);
        }
    }
    
    void OnDestroy()
    {
        if (allDoors.Contains(this))
        {
            allDoors.Remove(this);
        }
    }
    
    void Start()
    {
        if (audioSource == null)
        {
            audioSource = GetComponent<AudioSource>();
            if (audioSource == null)
            {
                audioSource = gameObject.AddComponent<AudioSource>();
                audioSource.playOnAwake = false;
                audioSource.spatialBlend = 1.0f;
                audioSource.minDistance = 1.0f;
                audioSource.maxDistance = 10.0f;
            }
        }
    }
    
    void Update()
    {
        UpdateAnimation();
        UpdateAutoClose();
    }
    
    void UpdateAnimation()
    {
        if (!isAnimating)
            return;
        
        if (currentState == DoorState.Opening || currentState == DoorState.Closing)
        {
            animationProgress += Time.deltaTime / animationDuration;
            float curveValue = animationCurve.Evaluate(animationProgress);
            
            if (currentState == DoorState.Opening)
            {
                doorTransform.localRotation = Quaternion.Slerp(closedRotation, openRotation, curveValue);
            }
            else
            {
                doorTransform.localRotation = Quaternion.Slerp(openRotation, closedRotation, curveValue);
            }
            
            if (animationProgress >= 1.0f)
            {
                animationProgress = 1.0f;
                isAnimating = false;
                
                if (currentState == DoorState.Opening)
                {
                    currentState = DoorState.Open;
                    OnDoorOpen?.Invoke();
                    
                    if (autoClose)
                    {
                        autoCloseTimer = autoCloseDelay;
                    }
                }
                else
                {
                    currentState = DoorState.Closed;
                    OnDoorClose?.Invoke();
                }
            }
        }
    }
    
    void UpdateAutoClose()
    {
        if (!autoClose || currentState != DoorState.Open)
            return;
        
        autoCloseTimer -= Time.deltaTime;
        if (autoCloseTimer <= 0.0f)
        {
            CloseDoor();
        }
    }
    
    public void ToggleDoor()
    {
        if (isAnimating)
            return;
        
        if (currentState == DoorState.Closed)
        {
            OpenDoor();
        }
        else if (currentState == DoorState.Open)
        {
            CloseDoor();
        }
    }
    
    public void OpenDoor()
    {
        if (isAnimating || currentState == DoorState.Open)
            return;
        
        currentState = DoorState.Opening;
        animationProgress = 0.0f;
        isAnimating = true;
        autoCloseTimer = 0.0f;
        
        PlaySound(openSound);
    }
    
    public void CloseDoor()
    {
        if (isAnimating || currentState == DoorState.Closed)
            return;
        
        currentState = DoorState.Closing;
        animationProgress = 0.0f;
        isAnimating = true;
        
        PlaySound(closeSound);
    }
    
    void PlaySound(AudioClip clip)
    {
        if (clip != null && audioSource != null)
        {
            audioSource.PlayOneShot(clip);
        }
    }
    
    public bool IsInRange(Vector3 playerPosition)
    {
        if (doorTransform == null)
            return false;
        
        float distance = Vector3.Distance(playerPosition, doorTransform.position);
        return distance <= interactDistance;
    }
    
    public bool IsInPromptRange(Vector3 playerPosition)
    {
        if (doorTransform == null)
            return false;
        
        float distance = Vector3.Distance(playerPosition, doorTransform.position);
        return distance <= promptDistance;
    }
    
    public bool IsOpen()
    {
        return currentState == DoorState.Open;
    }
    
    public bool IsClosed()
    {
        return currentState == DoorState.Closed;
    }
    
    public DoorState GetCurrentState()
    {
        return currentState;
    }
    
    public string GetDoorName()
    {
        return doorName;
    }
    
    public static List<DoorInteract> GetAllDoors()
    {
        return new List<DoorInteract>(allDoors);
    }
    
    public static DoorInteract FindNearestDoor(Vector3 playerPosition)
    {
        DoorInteract nearest = null;
        float minDistance = float.MaxValue;
        
        foreach (DoorInteract door in allDoors)
        {
            if (door == null || door.doorTransform == null)
                continue;
            
            float distance = Vector3.Distance(playerPosition, door.doorTransform.position);
            if (distance < minDistance)
            {
                minDistance = distance;
                nearest = door;
            }
        }
        
        return nearest;
    }
    
    public static DoorInteract FindDoorInRange(Vector3 playerPosition, float maxDistance)
    {
        DoorInteract nearest = null;
        float minDistance = maxDistance;
        
        foreach (DoorInteract door in allDoors)
        {
            if (door == null || door.doorTransform == null)
                continue;
            
            float distance = Vector3.Distance(playerPosition, door.doorTransform.position);
            if (distance <= maxDistance && distance < minDistance)
            {
                minDistance = distance;
                nearest = door;
            }
        }
        
        return nearest;
    }
}

public class DoorInteractionController : MonoBehaviour
{
    [Header("Settings")]
    public Transform cameraTransform;
    public float raycastDistance = 5.0f;
    public LayerMask doorLayer = ~0;
    public KeyCode interactKey = KeyCode.E;
    public bool useMouseClick = true;
    public int mouseButton = 0;
    
    [Header("UI")]
    public UnityEngine.UI.Text promptText;
    public string defaultPrompt = "按 E 开门";
    
    private Camera mainCamera;
    private DoorInteract currentDoor;
    
    void Start()
    {
        if (cameraTransform == null)
        {
            mainCamera = Camera.main;
            if (mainCamera != null)
            {
                cameraTransform = mainCamera.transform;
            }
        }
        
        if (promptText != null)
        {
            promptText.gameObject.SetActive(false);
        }
    }
    
    void Update()
    {
        CheckForDoor();
        HandleInteraction();
        UpdateUI();
    }
    
    void CheckForDoor()
    {
        if (cameraTransform == null)
        {
            currentDoor = null;
            return;
        }
        
        Ray ray = new Ray(cameraTransform.position, cameraTransform.forward);
        RaycastHit hit;
        
        if (Physics.Raycast(ray, out hit, raycastDistance, doorLayer))
        {
            currentDoor = hit.collider.GetComponentInParent<DoorInteract>();
        }
        else
        {
            currentDoor = DoorInteract.FindDoorInRange(transform.position, 3.0f);
        }
    }
    
    void HandleInteraction()
    {
        if (currentDoor == null)
            return;
        
        bool keyPressed = Input.GetKeyDown(interactKey);
        bool mousePressed = useMouseClick && Input.GetMouseButtonDown(mouseButton);
        
        if (keyPressed || mousePressed)
        {
            if (currentDoor.IsInRange(transform.position))
            {
                currentDoor.ToggleDoor();
            }
        }
    }
    
    void UpdateUI()
    {
        if (promptText == null)
            return;
        
        bool shouldShow = currentDoor != null && currentDoor.IsInPromptRange(transform.position);
        promptText.gameObject.SetActive(shouldShow);
        
        if (shouldShow)
        {
            string stateText = currentDoor.IsOpen() ? "关门" : "开门";
            promptText.text = string.Format("按 {0} {1}", interactKey, stateText);
        }
    }
}
