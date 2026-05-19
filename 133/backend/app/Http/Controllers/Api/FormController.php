<?php

namespace App\Http\Controllers\Api;

use App\Models\Form;
use App\Models\FormField;
use App\Models\FormVersion;
use Illuminate\Http\Request;
use App\Http\Controllers\Controller;
use Illuminate\Validation\ValidationException;

class FormController extends Controller
{
    public function __construct()
    {
        $this->middleware('auth:tenant');
    }

    public function index()
    {
        $forms = Form::with('creator', 'approvalFlow', 'currentVersion')
            ->where('created_by', auth('tenant')->id())
            ->orWhereHas('approvalFlow', function ($query) {
                $query->whereHas('steps', function ($q) {
                    $q->where('approver_id', auth('tenant')->id());
                });
            })
            ->paginate(10);

        return response()->json($forms);
    }

    public function store(Request $request)
    {
        $request->validate([
            'name' => 'required|string|max:255',
            'description' => 'nullable|string',
            'schema' => 'nullable|array',
            'fields' => 'required|array',
            'fields.*.label' => 'required|string',
            'fields.*.name' => 'required|string',
            'fields.*.type' => 'required|string',
            'fields.*.is_required' => 'boolean',
            'approval_flow_id' => 'nullable|exists:approval_flows,id',
            'change_note' => 'nullable|string',
        ]);

        $form = Form::create([
            'name' => $request->name,
            'description' => $request->description,
            'schema' => $request->schema,
            'is_published' => false,
            'created_by' => auth('tenant')->id(),
            'approval_flow_id' => $request->approval_flow_id,
        ]);

        foreach ($request->fields as $index => $field) {
            FormField::create([
                'form_id' => $form->id,
                'label' => $field['label'],
                'name' => $field['name'],
                'type' => $field['type'],
                'options' => $field['options'] ?? null,
                'is_required' => $field['is_required'] ?? false,
                'order' => $index,
                'validation' => $field['validation'] ?? null,
            ]);
        }

        $form->createVersion(auth('tenant')->id(), $request->change_note ?? 'Initial version');

        return response()->json([
            'message' => 'Form created successfully',
            'form' => $form->load('fields', 'creator', 'currentVersion'),
        ], 201);
    }

    public function show(Form $form)
    {
        return response()->json($form->load('fields', 'creator', 'approvalFlow.steps', 'currentVersion'));
    }

    public function update(Request $request, Form $form)
    {
        $request->validate([
            'name' => 'sometimes|string|max:255',
            'description' => 'nullable|string',
            'schema' => 'nullable|array',
            'is_published' => 'sometimes|boolean',
            'fields' => 'sometimes|array',
            'approval_flow_id' => 'nullable|exists:approval_flows,id',
            'change_note' => 'nullable|string',
        ]);

        $form->update($request->only(['name', 'description', 'schema', 'is_published', 'approval_flow_id']));

        if ($request->has('fields')) {
            $form->fields()->delete();
            
            foreach ($request->fields as $index => $field) {
                FormField::create([
                    'form_id' => $form->id,
                    'label' => $field['label'],
                    'name' => $field['name'],
                    'type' => $field['type'],
                    'options' => $field['options'] ?? null,
                    'is_required' => $field['is_required'] ?? false,
                    'order' => $index,
                    'validation' => $field['validation'] ?? null,
                ]);
            }
        }

        $form->createVersion(auth('tenant')->id(), $request->change_note ?? 'Updated form');

        return response()->json([
            'message' => 'Form updated successfully',
            'form' => $form->load('fields', 'currentVersion'),
        ]);
    }

    public function destroy(Form $form)
    {
        $form->delete();
        return response()->json([
            'message' => 'Form deleted successfully',
        ]);
    }

    public function publish(Form $form)
    {
        $form->update(['is_published' => true]);
        $form->createVersion(auth('tenant')->id(), 'Published');
        
        return response()->json([
            'message' => 'Form published successfully',
            'form' => $form->load('currentVersion'),
        ]);
    }

    public function versions(Form $form)
    {
        $versions = $form->versions()->with('creator')->paginate(10);
        
        return response()->json([
            'form' => $form->only(['id', 'name']),
            'versions' => $versions,
        ]);
    }

    public function showVersion(Form $form, FormVersion $version)
    {
        if ($version->form_id !== $form->id) {
            throw ValidationException::withMessages([
                'version' => 'Invalid version for this form',
            ]);
        }

        return response()->json($version->load('creator'));
    }

    public function rollback(Request $request, Form $form, FormVersion $version)
    {
        if ($version->form_id !== $form->id) {
            throw ValidationException::withMessages([
                'version' => 'Invalid version for this form',
            ]);
        }

        $newVersion = $form->rollbackToVersion($version->id, auth('tenant')->id());

        return response()->json([
            'message' => "Rolled back to version {$version->version_number} successfully",
            'form' => $form->load('fields', 'currentVersion'),
            'new_version' => $newVersion,
        ]);
    }

    public function compareVersions(Request $request, Form $form)
    {
        $request->validate([
            'version1_id' => 'required|exists:form_versions,id',
            'version2_id' => 'required|exists:form_versions,id',
        ]);
        
        $version1 = FormVersion::where('form_id', $form->id)->findOrFail($request->version1_id);
        $version2 = FormVersion::where('form_id', $form->id)->findOrFail($request->version2_id);

        return response()->json([
            'form' => $form->only(['id', 'name']),
            'version1' => $version1,
            'version2' => $version2,
        ]);
    }
}
