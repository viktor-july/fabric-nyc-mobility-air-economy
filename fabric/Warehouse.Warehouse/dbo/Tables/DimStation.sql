CREATE TABLE [dbo].[DimStation] (
    [location_id]       INT           NOT NULL,
    [location_name]     VARCHAR (100) NULL,
    [latitude]          FLOAT (53)    NULL,
    [longitude]         FLOAT (53)    NULL,
    [zone_id]           INT           NULL,
    [zone_borough]      VARCHAR (50)  NULL,
    [zone_name]         VARCHAR (100) NULL,
    [match_type]        VARCHAR (20)  NULL,
    [distance_km]       FLOAT (53)    NULL,
    [in_nyc]            BIT           NULL,
    [zone_link_quality] VARCHAR (20)  NULL
);


GO

ALTER TABLE [dbo].[DimStation]
    ADD CONSTRAINT [PK_DimStation] PRIMARY KEY NONCLUSTERED ([location_id] ASC) NOT ENFORCED;


GO