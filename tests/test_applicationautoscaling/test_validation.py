import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_applicationautoscaling, mock_ecs
from moto.applicationautoscaling import models
from moto.applicationautoscaling.exceptions import AWSValidationException

from .test_applicationautoscaling import register_scalable_target

DEFAULT_REGION = "us-east-1"
DEFAULT_ECS_CLUSTER = "default"
DEFAULT_ECS_TASK = "test_ecs_task"
DEFAULT_ECS_SERVICE = "sample-webapp"
DEFAULT_SERVICE_NAMESPACE = "ecs"
DEFAULT_RESOURCE_ID = f"service/{DEFAULT_ECS_CLUSTER}/{DEFAULT_ECS_SERVICE}"
DEFAULT_SCALABLE_DIMENSION = "ecs:service:DesiredCount"
DEFAULT_MIN_CAPACITY = 1
DEFAULT_MAX_CAPACITY = 1
DEFAULT_ROLE_ARN = "test:arn"


@mock_applicationautoscaling
def test_describe_scalable_targets_with_invalid_scalable_dimension_should_return_validation_exception():
    client = boto3.client("application-autoscaling", region_name=DEFAULT_REGION)

    with pytest.raises(ClientError) as ex:
        client.describe_scalable_targets(
            ServiceNamespace=DEFAULT_SERVICE_NAMESPACE, ScalableDimension="foo"
        )
    err = ex.value.response
    assert err["Error"]["Code"] == "ValidationException"
    assert "1 validation error detected" in err["Error"]["Message"]
    assert err["ResponseMetadata"]["HTTPStatusCode"] == 400


@mock_applicationautoscaling
def test_describe_scalable_targets_with_invalid_service_namespace_should_return_validation_exception():
    client = boto3.client("application-autoscaling", region_name=DEFAULT_REGION)

    with pytest.raises(ClientError) as ex:
        client.describe_scalable_targets(
            ServiceNamespace="foo", ScalableDimension=DEFAULT_SCALABLE_DIMENSION
        )
    err = ex.value.response
    assert err["Error"]["Code"] == "ValidationException"
    assert "1 validation error detected" in err["Error"]["Message"]
    assert err["ResponseMetadata"]["HTTPStatusCode"] == 400


@mock_applicationautoscaling
def test_describe_scalable_targets_with_multiple_invalid_parameters_should_return_validation_exception():
    client = boto3.client("application-autoscaling", region_name=DEFAULT_REGION)

    with pytest.raises(ClientError) as ex:
        client.describe_scalable_targets(
            ServiceNamespace="foo", ScalableDimension="bar"
        )
    err = ex.value.response
    assert err["Error"]["Code"] == "ValidationException"
    assert "2 validation errors detected" in err["Error"]["Message"]
    assert err["ResponseMetadata"]["HTTPStatusCode"] == 400


@mock_ecs
@mock_applicationautoscaling
def test_register_scalable_target_ecs_with_non_existent_service_should_return_clusternotfound_exception():
    client = boto3.client("application-autoscaling", region_name=DEFAULT_REGION)
    resource_id = f"service/{DEFAULT_ECS_CLUSTER}/foo"

    with pytest.raises(ClientError) as ex:
        register_scalable_target(client, ServiceNamespace="ecs", ResourceId=resource_id)
    err = ex.value.response
    assert err["Error"]["Code"] == "ClusterNotFoundException"
    assert err["Error"]["Message"] == "Cluster not found."
    assert err["ResponseMetadata"]["HTTPStatusCode"] == 400


@pytest.mark.parametrize(
    "namespace,r_id,dimension,expected",
    [
        ("ecs", "service/default/test-svc", "ecs:service:DesiredCount", True),
        ("ecs", "banana/default/test-svc", "ecs:service:DesiredCount", False),
        ("rds", "service/default/test-svc", "ecs:service:DesiredCount", False),
    ],
)
def test_target_params_are_valid_success(namespace, r_id, dimension, expected):
    if expected is True:
        assert models._target_params_are_valid(namespace, r_id, dimension) == expected
    else:
        with pytest.raises(AWSValidationException):
            models._target_params_are_valid(namespace, r_id, dimension)


# TODO add a test for not-supplied MinCapacity or MaxCapacity (ValidationException)
