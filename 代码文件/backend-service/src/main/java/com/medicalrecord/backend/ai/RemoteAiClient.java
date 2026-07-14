package com.medicalrecord.backend.ai;

import com.fasterxml.jackson.annotation.JsonAlias;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.medicalrecord.backend.cases.CaseInput;
import com.medicalrecord.backend.config.AiProperties;
import org.springframework.http.HttpStatusCode;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.reactive.function.client.WebClientRequestException;
import org.springframework.web.reactive.function.client.WebClientResponseException;
import reactor.core.publisher.Mono;
import reactor.util.retry.Retry;

import java.time.Duration;
import java.util.List;
import java.util.concurrent.TimeoutException;

@Component
public class RemoteAiClient implements AiClient {
    private final AiProperties properties;
    private final WebClient webClient;

    public RemoteAiClient(AiProperties properties, WebClient.Builder builder) {
        this.properties = properties;
        this.webClient = builder.baseUrl(properties.baseUrl()).build();
    }

    @Override
    public AiAnalysisResult analyze(CaseInput input) {
        try {
            AiResponse response = webClient.post()
                    .uri(properties.endpoint())
                    .bodyValue(AiRequest.from(input))
                    .retrieve()
                    .onStatus(HttpStatusCode::is4xxClientError,
                            clientResponse -> Mono.error(new AiServiceException(
                                    "AI_PROCESSING_FAILED", "AI 服务拒绝了分析请求")))
                    .bodyToMono(AiResponse.class)
                    .timeout(properties.timeout())
                    .retryWhen(Retry.fixedDelay(1, Duration.ofMillis(500))
                            .filter(this::isRetryable)
                            .onRetryExhaustedThrow((spec, signal) -> signal.failure()))
                    .block();
            return validateAndMap(response);
        } catch (AiServiceException exception) {
            throw exception;
        } catch (RuntimeException exception) {
            Throwable cause = rootCause(exception);
            if (cause instanceof TimeoutException) {
                throw new AiServiceException("AI_TIMEOUT", "AI 分析服务响应超时");
            }
            throw new AiServiceException("AI_PROCESSING_FAILED", "AI 分析服务暂时不可用");
        }
    }

    private boolean isRetryable(Throwable throwable) {
        return throwable instanceof TimeoutException
                || throwable instanceof WebClientRequestException
                || throwable instanceof WebClientResponseException responseException
                && responseException.getStatusCode().is5xxServerError();
    }

    private AiAnalysisResult validateAndMap(AiResponse response) {
        if (response == null || isBlank(response.generatedRecord()) || isBlank(response.diagnosisTop1())) {
            throw new AiServiceException("AI_PROCESSING_FAILED", "AI 服务返回结果缺少必要字段");
        }
        return new AiAnalysisResult(
                response.generatedRecord(),
                response.symptoms(),
                response.medicalTerms(),
                response.diagnosisTop1(),
                response.diagnosisCandidates(),
                response.diagnosisReason(),
                response.treatmentAdvice(),
                response.content(),
                response.modelVersion() == null ? "unknown" : response.modelVersion(),
                response.confidence() == null ? 0.0 : response.confidence(),
                Boolean.TRUE.equals(response.lowConfidence()),
                response.lowConfidenceReason()
        );
    }

    private Throwable rootCause(Throwable throwable) {
        Throwable current = throwable;
        while (current.getCause() != null && current.getCause() != current) {
            current = current.getCause();
        }
        return current;
    }

    private boolean isBlank(String value) {
        return value == null || value.isBlank();
    }

    private record AiRequest(
            String name,
            String gender,
            Integer age,
            String department,
            @JsonProperty("visit_date") String visitDate,
            @JsonProperty("chief_complaint") String chiefComplaint,
            @JsonProperty("history_present_illness") String historyPresentIllness,
            @JsonProperty("past_history") String pastHistory,
            @JsonProperty("allergy_history") String allergyHistory,
            @JsonProperty("vital_signs") String vitalSigns,
            @JsonProperty("physical_exam") String physicalExam,
            @JsonProperty("lab_results") String labResults,
            @JsonProperty("preliminary_diagnosis") String preliminaryDiagnosis,
            @JsonProperty("treatment_taken") String treatmentTaken,
            @JsonProperty("medication_usage") String medicationUsage,
            @JsonProperty("generation_needs") List<String> generationNeeds
    ) {
        private static AiRequest from(CaseInput input) {
            return new AiRequest(
                    input.patientName(),
                    input.gender().value().equals("male") ? "男" : "女",
                    input.age(),
                    input.department() == null ? null : input.department().value(),
                    input.visitDate() == null ? null : input.visitDate().toString(),
                    input.chiefComplaint(),
                    input.presentIllness(),
                    input.pastHistory(),
                    input.allergyHistory(),
                    input.vitalSigns(),
                    input.physicalExam(),
                    input.auxiliaryExam(),
                    input.preliminaryDiagnosis(),
                    input.treatmentTaken(),
                    input.medicationUsage(),
                    input.generationNeeds().stream().map(need -> need.value()).toList()
            );
        }
    }

    private record AiResponse(
            @JsonAlias("generatedRecord") @JsonProperty("generated_record") String generatedRecord,
            List<String> symptoms,
            @JsonAlias("medicalTerms") @JsonProperty("medical_terms") List<String> medicalTerms,
            @JsonAlias("diagnosisTop1") @JsonProperty("diagnosis_top1") String diagnosisTop1,
            @JsonAlias("diagnosisCandidates") @JsonProperty("diagnosis_candidates") List<String> diagnosisCandidates,
            @JsonAlias("diagnosisReason") @JsonProperty("diagnosis_reason") String diagnosisReason,
            @JsonAlias("treatmentAdvice") @JsonProperty("treatment_advice") String treatmentAdvice,
            String content,
            @JsonAlias("modelVersion") @JsonProperty("model_version") String modelVersion,
            Double confidence,
            @JsonAlias("lowConfidence") @JsonProperty("low_confidence") Boolean lowConfidence,
            @JsonAlias("lowConfidenceReason") @JsonProperty("low_confidence_reason") String lowConfidenceReason
    ) {
    }
}
