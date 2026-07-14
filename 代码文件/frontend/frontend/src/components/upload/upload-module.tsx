import { DownOutlined, PaperClipOutlined } from "@ant-design/icons";
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import type { FieldValue, MedicalFormValues } from "../../types/medical-record";
import { MedicalApiError } from "../../services/medical-api";
import {
  medicalFieldConfigs,
  medicalFieldGroups,
  type MedicalFieldConfig,
} from "./form-config";

type UploadModuleProps = {
  isLoggedIn: boolean;
  onGenerate: (values: MedicalFormValues) => Promise<{ id: string }>;
  onRequireLogin: () => void;
};

type SubmitStatus = "idle" | "invalid" | "submitting" | "failed" | "authRequired";

function createInitialValues(): MedicalFormValues {
  return medicalFieldConfigs.reduce<MedicalFormValues>((values, field) => {
    values[field.key] = field.type === "multiselect" || field.type === "file" ? [] : "";
    return values;
  }, {});
}

function validateValues(values: MedicalFormValues) {
  return medicalFieldConfigs.reduce<Record<string, string>>((errors, field) => {
    const value = values[field.key];
    const textValue = Array.isArray(value)
      ? value.map((item) => typeof item === "string" ? item : item.name).join("")
      : value.trim();

    if (field.required && !textValue) {
      errors[field.key] = field.errorMessage ?? `请填写${field.label}`;
      return errors;
    }

    if (field.type === "number" && textValue) {
      const numberValue = Number(textValue);
      if (
        Number.isNaN(numberValue) ||
        !Number.isInteger(numberValue) ||
        (field.min !== undefined && numberValue < field.min) ||
        (field.max !== undefined && numberValue > field.max)
      ) {
        errors[field.key] = field.errorMessage ?? `${field.label}超出有效范围`;
      }
    }

    if (field.type === "file" && Array.isArray(value)) {
      const files = value.filter((item): item is File => typeof item !== "string");
      const totalSize = files.reduce((sum, file) => sum + file.size, 0);
      if (files.length > 5) errors[field.key] = "最多上传 5 个附件";
      else if (files.some((file) => file.size > 10 * 1024 * 1024)) errors[field.key] = "单个附件不能超过 10 MB";
      else if (totalSize > 30 * 1024 * 1024) errors[field.key] = "附件总大小不能超过 30 MB";
    }

    return errors;
  }, {});
}

function stringList(value: FieldValue): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string")
    : [];
}

export function UploadModule({ isLoggedIn, onGenerate, onRequireLogin }: UploadModuleProps) {
  const navigate = useNavigate();
  const [expanded, setExpanded] = useState(false);
  const [values, setValues] = useState<MedicalFormValues>(createInitialValues);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [status, setStatus] = useState<SubmitStatus>("idle");
  const [failureMessage, setFailureMessage] = useState("");
  const [fileInputVersion, setFileInputVersion] = useState(0);

  const visibleFields = medicalFieldConfigs.filter((field) => expanded || field.defaultVisible);
  const visibleGroups = medicalFieldGroups.filter((group) =>
    visibleFields.some((field) => field.group === group.key),
  );

  function updateFieldValue(fieldKey: string, nextValue: FieldValue) {
    setValues((current) => ({ ...current, [fieldKey]: nextValue }));
    setErrors((current) => {
      if (!current[fieldKey]) return current;
      const nextErrors = { ...current };
      delete nextErrors[fieldKey];
      return nextErrors;
    });
    if (status === "invalid") setStatus("idle");
    setFailureMessage("");
  }

  function toggleMultiSelect(fieldKey: string, optionValue: string) {
    const current = values[fieldKey];
    const list = stringList(current);
    updateFieldValue(
      fieldKey,
      list.includes(optionValue)
        ? list.filter((item) => item !== optionValue)
        : [...list, optionValue],
    );
  }

  function clearForm() {
    setValues(createInitialValues());
    setErrors({});
    setStatus("idle");
    setFailureMessage("");
    setExpanded(false);
    setFileInputVersion((version) => version + 1);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!isLoggedIn) {
      setStatus("authRequired");
      onRequireLogin();
      return;
    }
    const nextErrors = validateValues(values);

    if (Object.keys(nextErrors).length > 0) {
      setErrors(nextErrors);
      setStatus("invalid");
      setExpanded(true);
      requestAnimationFrame(() => {
        document.getElementById(`field-${Object.keys(nextErrors)[0]}`)?.focus();
      });
      return;
    }

    setStatus("submitting");
    setFailureMessage("");
    try {
      const record = await onGenerate(values);
      navigate(`/results/${record.id}`);
    } catch (error) {
      if (error instanceof MedicalApiError && Object.keys(error.fieldErrors).length > 0) {
        setErrors(error.fieldErrors);
        setExpanded(true);
        setStatus("invalid");
        requestAnimationFrame(() => {
          document.getElementById(`field-${Object.keys(error.fieldErrors)[0]}`)?.focus();
        });
        return;
      }
      setStatus("failed");
      setFailureMessage(error instanceof Error ? error.message : "服务暂时不可用，请稍后重试。");
    }
  }

  function renderField(field: MedicalFieldConfig) {
    const inputId = `field-${field.key}`;
    const errorId = `${inputId}-error`;
    const fieldValue = values[field.key];
    const fieldError = errors[field.key];
    const className = field.fullWidth ? "form-field form-field--full" : "form-field";
    const describedBy = fieldError ? errorId : undefined;

    return (
      <div className={fieldError ? `${className} has-error` : className} key={field.key}>
        <label className="form-field__label" htmlFor={inputId}>
          <span>{field.label}{field.unit ? <small>（{field.unit}）</small> : null}</span>
          {field.required ? <em aria-label="必填">*</em> : <span className="optional-label">选填</span>}
        </label>

        {field.type === "text" || field.type === "number" || field.type === "date" ? (
          <input
            aria-describedby={describedBy}
            aria-invalid={Boolean(fieldError)}
            className="form-input"
            id={inputId}
            max={field.max}
            maxLength={field.maxLength}
            min={field.min}
            placeholder={field.placeholder}
            step={field.key === "age" ? 1 : undefined}
            type={field.type}
            value={typeof fieldValue === "string" ? fieldValue : ""}
            onChange={(event) => updateFieldValue(field.key, event.target.value)}
          />
        ) : null}

        {field.type === "select" ? (
          <select
            aria-describedby={describedBy}
            aria-invalid={Boolean(fieldError)}
            className="form-input form-select"
            id={inputId}
            value={typeof fieldValue === "string" ? fieldValue : ""}
            onChange={(event) => updateFieldValue(field.key, event.target.value)}
          >
            <option value="">{field.placeholder ?? `请选择${field.label}`}</option>
            {field.options?.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
          </select>
        ) : null}

        {field.type === "textarea" ? (
          <textarea
            aria-describedby={describedBy}
            aria-invalid={Boolean(fieldError)}
            className="form-input form-textarea"
            id={inputId}
            maxLength={field.maxLength}
            placeholder={field.placeholder}
            value={typeof fieldValue === "string" ? fieldValue : ""}
            onChange={(event) => updateFieldValue(field.key, event.target.value)}
          />
        ) : null}

        {field.type === "multiselect" ? (
          <div className="multi-select" id={inputId} role="group" aria-label={field.label}>
            {field.options?.map((option) => {
              const active = stringList(fieldValue).includes(option.value);
              return (
                <button
                  aria-pressed={active}
                  className={active ? "multi-select__chip is-active" : "multi-select__chip"}
                  key={option.value}
                  type="button"
                  onClick={() => toggleMultiSelect(field.key, option.value)}
                >
                  {option.label}
                </button>
              );
            })}
          </div>
        ) : null}

        {field.type === "file" ? (
          <div className="file-field">
            <label className="file-field__trigger" htmlFor={inputId}><PaperClipOutlined />选择检查资料</label>
            <input
              accept=".pdf,.doc,.docx,.jpg,.jpeg,.png"
              className="file-field__input"
              id={inputId}
              key={fileInputVersion}
              multiple
              type="file"
              onChange={(event) => updateFieldValue(
                field.key,
                Array.from(event.target.files ?? []),
              )}
            />
            <span className="file-field__hint">
              {Array.isArray(fieldValue) && fieldValue.length > 0
                ? fieldValue.map((item) => typeof item === "string" ? item : item.name).join(" / ")
                : "支持 PDF / DOC / DOCX / JPG / PNG，最多 5 个文件"}
            </span>
          </div>
        ) : null}

        {fieldError ? <span className="field-error" id={errorId} role="alert">{fieldError}</span> : null}
      </div>
    );
  }

  return (
    <section className="upload-section" aria-labelledby="intake-title">
      <form className={expanded ? "upload-panel is-expanded" : "upload-panel"} noValidate onSubmit={handleSubmit}>
        <div className="upload-panel__header">
          <div className="upload-panel__heading">
            <span className="upload-panel__eyebrow">Structured Intake</span>
            <h2 id="intake-title">填写病例，生成专业分析</h2>
            <p>填写患者信息，系统将生成标准病历与辅助分析结果。</p>
          </div>
          <button
            aria-expanded={expanded}
            className={expanded ? "upload-panel__toggle is-expanded" : "upload-panel__toggle"}
            type="button"
            onClick={() => setExpanded((current) => !current)}
          >
            <span>{expanded ? "收起完整信息" : "填写完整信息"}</span><DownOutlined />
          </button>
        </div>

        <div className="upload-panel__body">
          {visibleGroups.map((group) => (
            <fieldset className="form-group" key={group.key}>
              <legend className="form-group__header">
                <span>{group.title}</span>
                <small>{group.description}</small>
              </legend>
              <div className={group.key === "patient" ? "form-grid form-grid--patient" : "form-grid"}>
                {visibleFields.filter((field) => field.group === group.key).map(renderField)}
              </div>
            </fieldset>
          ))}
        </div>

        <div className="upload-panel__footer">
          <div className="form-feedback" aria-live="polite">
            {status === "invalid" ? <span className="form-status form-status--error">请完成标记的必填信息后再生成。</span> : null}
            {status === "submitting" ? <span className="form-status">正在整理病例信息…</span> : null}
            {status === "failed" ? <span className="form-status form-status--error">{failureMessage || "服务暂时不可用，请稍后重试。"}</span> : null}
            {status === "authRequired" ? <span className="form-status form-status--error">请先登录后再生成病例分析。</span> : null}
            {status === "idle" && !expanded ? <span>完整生成还需填写现病史；既往病史未填写时将标记为未提供。</span> : null}
          </div>
          <div className="form-actions">
            <button className="secondary-button" type="button" onClick={clearForm}>清空内容</button>
            <button className="primary-button" type="submit" disabled={status === "submitting"}>
              {status === "submitting" ? "正在生成" : "生成病历并分析"}
            </button>
          </div>
        </div>
      </form>
    </section>
  );
}
