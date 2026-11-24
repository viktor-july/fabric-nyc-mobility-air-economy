CREATE TABLE [dbo].[FactAirQualityDaily] (
    [date_key]    INT        NULL,
    [location_id] BIGINT     NULL,
    [pm25_avg]    FLOAT (53) NULL,
    [no2_avg]     FLOAT (53) NULL,
    [o3_avg]      FLOAT (53) NULL,
    [co_avg]      FLOAT (53) NULL,
    [so2_avg]     FLOAT (53) NULL,
    [pm10_avg]    FLOAT (53) NULL,
    [no_avg]      FLOAT (53) NULL,
    [nox_avg]     FLOAT (53) NULL
);


GO