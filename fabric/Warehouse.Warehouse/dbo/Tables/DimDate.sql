CREATE TABLE [dbo].[DimDate] (
    [date_key]    INT          NOT NULL,
    [date]        DATE         NOT NULL,
    [year]        INT          NOT NULL,
    [quarter]     INT          NOT NULL,
    [month]       INT          NOT NULL,
    [month_name]  VARCHAR (20) NOT NULL,
    [day]         INT          NOT NULL,
    [day_of_week] INT          NOT NULL,
    [day_name]    VARCHAR (20) NOT NULL,
    [is_weekend]  BIT          NOT NULL,
    [season]      VARCHAR (10) NOT NULL
);


GO

ALTER TABLE [dbo].[DimDate]
    ADD CONSTRAINT [PK_DimDate] PRIMARY KEY NONCLUSTERED ([date_key] ASC) NOT ENFORCED;


GO